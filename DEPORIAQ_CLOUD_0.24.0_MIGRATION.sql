-- ADAY SÜRÜM: önce ayrı test projesinde çalıştırın. İşletme geçişini otomatik açmaz.
begin;
-- 001_commerce.sql
-- DeporiaQ 0.24.0 CANDIDATE. Test project first. Requires existing 0.22.4 schema.
-- Additive migration: does NOT enable commerce or extend existing subscriptions.
create schema if not exists dpq;
revoke all on schema dpq from public, anon, authenticated;
create table if not exists dpq.settings (
 company_id uuid primary key references public.companies(id), enabled boolean not null default false,
 center_id uuid references public.locations(id), billing_ready boolean not null default false
);
create table if not exists dpq.plans (code text primary key, devices integer not null check(devices>0));
insert into dpq.plans values ('demo',1),('single',1),('duo',3),('plus',6),('ultra',20) on conflict do nothing;
create table if not exists dpq.devices (
 company_id uuid references public.companies(id), code text, name text not null,
 user_id uuid not null, active boolean not null default true, seen_at timestamptz not null default now(),
 primary key(company_id,code)
);
create table if not exists dpq.staff_locations (
 company_id uuid references public.companies(id), user_id uuid, location_id uuid references public.locations(id),
 primary key(company_id,user_id,location_id)
);
create table if not exists dpq.channels (
 id uuid primary key default gen_random_uuid(), company_id uuid not null references public.companies(id),
 name text not null check(length(name) between 1 and 100), active boolean not null default true,
 mode text not null default 'manual' check(mode='manual'), unique(company_id,name)
);
create table if not exists dpq.channel_locations (
 channel_id uuid references dpq.channels(id), location_id uuid references public.locations(id),
 buffer numeric not null default 0 check(buffer>=0), primary key(channel_id,location_id)
);
create table if not exists dpq.orders (
 id uuid primary key default gen_random_uuid(), company_id uuid not null references public.companies(id),
 channel_id uuid references dpq.channels(id), reference text not null, customer text not null,
 address text not null default '', status text not null default 'reserved',
 shipping text not null check(shipping in ('consolidate','split')), center_id uuid references public.locations(id),
 paid boolean not null default false, expires_at timestamptz, created_at timestamptz not null default now(),
 unique(company_id,channel_id,reference),
 check(status in ('reserved','preparing','shipped','completed','cancelled','expired'))
);
create table if not exists dpq.allocations (
 id uuid primary key default gen_random_uuid(), order_id uuid not null references dpq.orders(id),
 product_id uuid not null references public.products(id), location_id uuid not null references public.locations(id),
 quantity numeric not null check(quantity>0), unit_price numeric not null, unit_cost numeric not null,
 state text not null default 'reserved' check(state in ('reserved','transit','shipped','released','returned')),
 target_id uuid references public.locations(id), carrier text, tracking text
);
create table if not exists dpq.sales_ledger (
 id uuid primary key, company_id uuid not null, product_id uuid not null references public.products(id),
 location_id uuid not null references public.locations(id), quantity numeric not null check(quantity>0),
 kind text not null check(kind in ('sale','return')), unit_price numeric not null,unit_cost numeric not null,
 order_id uuid references dpq.orders(id), created_at timestamptz not null default now()
);
create table if not exists dpq.operations (
 company_id uuid, request_id uuid, actor uuid not null, action text not null, payload jsonb not null,
 result jsonb, created_at timestamptz not null default now(), primary key(company_id,request_id)
);
create table if not exists dpq.audit (
 id bigint generated always as identity primary key, company_id uuid not null,
 actor uuid not null, action text not null, payload jsonb not null, created_at timestamptz not null default now()
);
create table if not exists dpq.tickets (
 id uuid primary key default gen_random_uuid(), company_id uuid not null, actor uuid not null,
 subject text not null, message text not null, contact text not null, created_at timestamptz not null default now(),
 mail_status text not null default 'pending' check(mail_status in ('pending','sent','failed'))
);
create table if not exists dpq.renewal_preferences (
 company_id uuid primary key references public.companies(id), renew boolean not null default true,
 updated_at timestamptz not null default now()
);
create table if not exists dpq.payments (
 provider_event text primary key, company_id uuid not null, order_id text unique not null,
 amount_minor bigint not null check(amount_minor>0), currency text not null, plan text not null references dpq.plans(code),
 period_end timestamptz not null, created_at timestamptz not null default now()
);
create table if not exists dpq.checkout_orders (
 id uuid primary key default gen_random_uuid(), company_id uuid not null, plan text not null references dpq.plans(code),
 amount_minor bigint not null check(amount_minor>0), currency text not null default 'TRY',
 period_end timestamptz not null, paid boolean not null default false
);
-- No client table writes. Only the checked RPC below can mutate commerce state.
revoke all on all tables in schema dpq from public, anon, authenticated;
revoke all on all sequences in schema dpq from public, anon, authenticated;

create or replace function dpq.available(c uuid,p uuid,l uuid) returns numeric
language sql stable set search_path='' as $$
 select coalesce((select quantity from public.inventory where company_id=c and product_id=p and location_id=l),0)
 - coalesce((select sum(a.quantity) from dpq.allocations a join dpq.orders o on o.id=a.order_id
 where o.company_id=c and a.product_id=p and a.location_id=l and a.state='reserved'),0)
$$;

create or replace function dpq.guard_legacy() returns trigger
language plpgsql security definer set search_path='' as $$
declare c uuid;
begin
 if tg_op='UPDATE' and old.company_id is distinct from new.company_id then
 raise exception 'DPQ_TENANT: Şirket kimliği değiştirilemez'; end if;
 c:=case when tg_op='DELETE' then old.company_id else new.company_id end;
 if exists(select 1 from dpq.settings where company_id=c and enabled)
 and coalesce(current_setting('dpq.internal',true),'') <> c::text then
  raise exception 'DPQ_SERVER_ONLY: Eski stok/cihaz yazımı kapalı. Güncel sunucu işlemini kullanın.';
 end if;
 if tg_op='DELETE' then return old; end if; return new;
end $$;
do $$ declare t text; begin
 foreach t in array array['inventory','products','locations','cloud_devices'] loop
 execute format('drop trigger if exists dpq_guard_legacy on public.%I',t);
 execute format('create trigger dpq_guard_legacy before insert or update or delete on public.%I for each row execute function dpq.guard_legacy()',t);
 end loop;
end $$;

create or replace function public.dpq_call(p_action text,p_payload jsonb default '{}',p_device text default '')
returns jsonb language plpgsql security definer set search_path='' as $$
declare
 c uuid; u uuid:=auth.uid(); role_name text; conf dpq.settings%rowtype; sub public.company_subscriptions%rowtype;
 max_devices integer; allowed boolean; enabled boolean; oid uuid; pid uuid; lid uuid; target uuid; ch uuid;
 qty numeric; remaining numeric; take_qty numeric; result jsonb; req uuid; prior dpq.operations%rowtype;
 r record; item jsonb; alloc dpq.allocations%rowtype; ord dpq.orders%rowtype; admin boolean;
begin
 if u is null then raise exception 'DPQ_AUTH: Oturum açın'; end if;
 if (select count(*) from public.company_members where user_id=u and active)<>1 then
 raise exception 'DPQ_COMPANY: Tek ve etkin şirket üyeliği gerekli'; end if;
 select company_id,role into c,role_name from public.company_members where user_id=u and active;
 admin:=role_name in ('owner','admin');
 insert into dpq.settings(company_id) values(c) on conflict do nothing;
 -- One company lock serializes device grants, POS, reservations, transfers and payment state.
 select * into conf from dpq.settings where company_id=c for update;
 enabled:=conf.enabled;
 select * into sub from public.company_subscriptions where company_id=c;
 select devices into max_devices from dpq.plans where code=sub.plan_code;
 allowed:=coalesce(sub.status in ('trial','active','past_due') and sub.valid_until>clock_timestamp(),false);
 if p_action='status' then
 return jsonb_build_object('enabled',enabled,'company_id',c,'role',role_name,'allowed',allowed,
 'plan',sub.plan_code,'valid_until',sub.valid_until,'server_time',clock_timestamp(),
 'device_limit',max_devices,'devices_used',(select count(*) from dpq.devices where company_id=c and active),
 'billing_ready',conf.billing_ready,'renew',coalesce((select renew from dpq.renewal_preferences where company_id=c),true));
 end if;
 if p_action='operation_status' then
 select * into prior from dpq.operations where company_id=c and request_id=(p_payload->>'request_id')::uuid and actor=u;
 if not found then return '{"found":false}'; end if;
 return jsonb_build_object('found',true,'result',prior.result);
 end if;
 if not enabled then raise exception 'DPQ_NOT_READY: Bu işletme için yeni altyapı henüz etkinleştirilmedi'; end if;
 if p_action='support' then
 if length(trim(coalesce(p_payload->>'subject',''))) not between 3 and 200
 or length(trim(coalesce(p_payload->>'message',''))) not between 5 and 10000
 or length(coalesce(p_payload->>'contact','')) not between 3 and 300 then raise exception 'DPQ_INPUT: Destek alanlarını doldurun'; end if;
 end if;
 -- Support and renewal remain accessible after expiration. All operational calls fail closed.
 if p_action not in ('support','renewal','devices') and (not allowed or max_devices is null) then
 raise exception 'DPQ_LICENSE: Abonelik sona erdi veya paket atanmamış'; end if;
 if p_action='register' then
 if length(p_device) not between 8 and 160 then raise exception 'DPQ_DEVICE: Geçersiz cihaz'; end if;
 if exists(select 1 from dpq.devices where company_id=c and code=p_device and not active) then
 raise exception 'DPQ_DEVICE: Cihaz devre dışı'; end if;
 if not exists(select 1 from dpq.devices where company_id=c and code=p_device) then
 if (select count(*) from dpq.devices where company_id=c and active)>=max_devices then raise exception 'DPQ_LIMIT: Cihaz sınırı dolu'; end if;
 insert into dpq.devices(company_id,code,name,user_id) values(c,p_device,left(coalesce(p_payload->>'name','Bilgisayar'),100),u);
 end if;
 update dpq.devices set seen_at=clock_timestamp() where company_id=c and code=p_device;
 return jsonb_build_object('registered',true);
 end if;
 if p_action not in ('support','renewal','devices') and not exists(select 1 from dpq.devices where company_id=c and code=p_device and active) then
 raise exception 'DPQ_DEVICE: Etkin cihaz kaydı gerekli'; end if;
 if p_action='devices' then
 if not admin then raise exception 'DPQ_ROLE: Yönetici gerekli'; end if;
 return coalesce((select jsonb_agg(to_jsonb(d)-'user_id') from dpq.devices d where company_id=c),'[]');
 end if;
 -- Expired unpaid reservations are released atomically before any stock decision.
 update dpq.allocations a set state='released' from dpq.orders o where a.order_id=o.id and o.company_id=c
 and o.status='reserved' and not o.paid and o.expires_at<=clock_timestamp() and a.state='reserved';
 update dpq.orders set status='expired' where company_id=c and status='reserved' and not paid and expires_at<=clock_timestamp();
 if p_action='snapshot' then
 return jsonb_build_object(
 'products',coalesce((select jsonb_agg(to_jsonb(p)) from public.products p where company_id=c),'[]'),
 'locations',coalesce((select jsonb_agg(to_jsonb(l)) from public.locations l where company_id=c),'[]'),
 'inventory',coalesce((select jsonb_agg(to_jsonb(i)||jsonb_build_object('available',dpq.available(c,i.product_id,i.location_id))) from public.inventory i where company_id=c),'[]'),
 'sales',coalesce((select jsonb_agg(to_jsonb(e)) from dpq.sales_ledger e where company_id=c and admin),'[]'),
 'channels',coalesce((select jsonb_agg(to_jsonb(x)) from dpq.channels x where company_id=c),'[]'),
 'orders',coalesce((select jsonb_agg(to_jsonb(o)||jsonb_build_object('allocations',coalesce((select jsonb_agg(to_jsonb(a)) from dpq.allocations a where a.order_id=o.id),'[]'))) from dpq.orders o where company_id=c and admin),'[]'));
 end if;
 if p_action not in ('support','renewal') and role_name not in ('owner','admin','manager','employee','warehouse','branch') then raise exception 'DPQ_ROLE: Salt okunur hesap'; end if;
 if p_action in ('channel_save','channel_archive','catalog_product','catalog_location','count','receive','device_disable','renewal') and not admin then raise exception 'DPQ_ROLE: Yönetici gerekli'; end if;
 if not admin and p_action not in ('sale','transfer','support') then
 raise exception 'DPQ_ROLE: Bu aday sürümde sipariş yönetimi yetkili işletme yöneticisine açıktır'; end if;
 if not admin and p_action in ('sale','transfer') then
 if not exists(select 1 from dpq.staff_locations where company_id=c and user_id=u and location_id=(p_payload->>'location_id')::uuid) then
 raise exception 'DPQ_LOCATION_ROLE: Bu konumda işlem yetkiniz yok'; end if;
 if p_action='sale' and role_name not in ('branch','employee','manager') then raise exception 'DPQ_ROLE: Satış yetkisi yok'; end if;
 if p_action='transfer' and role_name not in ('warehouse','employee','manager') then raise exception 'DPQ_ROLE: Transfer yetkisi yok'; end if;
 end if;
 if sub.plan_code='demo' and p_action not in ('sale','receive','catalog_product','support','renewal') then raise exception 'DPQ_DEMO: Bu özellik ücretli paket gerektirir'; end if;
 req:=(p_payload->>'request_id')::uuid;
 if req is null then raise exception 'DPQ_REQUEST: İşlem kimliği gerekli'; end if;
 select * into prior from dpq.operations where company_id=c and request_id=req;
 if found then
 if prior.action<>p_action or prior.payload<>p_payload or prior.actor<>u then raise exception 'DPQ_REPLAY: İşlem kimliği farklı içerikle tekrar kullanıldı'; end if;
 return prior.result;
 end if;
 perform set_config('dpq.internal',c::text,true);
 pid:=nullif(p_payload->>'product_id','')::uuid;
 lid:=nullif(p_payload->>'location_id','')::uuid;
 target:=nullif(p_payload->>'target_id','')::uuid;
 qty:=nullif(p_payload->>'quantity','')::numeric;
 if pid is not null and not exists(select 1 from public.products where id=pid and company_id=c and active) then raise exception 'DPQ_PRODUCT: Geçersiz ürün'; end if;
 if lid is not null and not exists(select 1 from public.locations where id=lid and company_id=c and active) then raise exception 'DPQ_LOCATION: Geçersiz konum'; end if;
 if target is not null and not exists(select 1 from public.locations where id=target and company_id=c and active) then raise exception 'DPQ_LOCATION: Geçersiz hedef'; end if;
 if p_action in ('sale','receive','count','transfer') then
 if pid is null or lid is null or qty is null or qty='NaN'::numeric or qty>1000000 or qty<0 or (p_action<>'count' and qty=0) or trunc(qty)<>qty then raise exception 'DPQ_INPUT: Geçersiz miktar'; end if;
 insert into public.inventory(company_id,product_id,location_id,quantity) values(c,pid,lid,0) on conflict(company_id,location_id,product_id) do nothing;
 if p_action in ('sale','transfer') and dpq.available(c,pid,lid)<qty then raise exception 'DPQ_STOCK: Satılabilir stok yetersiz'; end if;
 if p_action='count' and qty < (select quantity from public.inventory where company_id=c and product_id=pid and location_id=lid)-dpq.available(c,pid,lid) then raise exception 'DPQ_RESERVED: Sayım ayrılmış stoğun altına düşüyor; önce eksik siparişi çözün'; end if;
 if p_action='transfer' then
 if target is null or target=lid then raise exception 'DPQ_LOCATION: Farklı hedef gerekli'; end if;
 insert into public.inventory(company_id,product_id,location_id,quantity) values(c,pid,target,qty)
 on conflict(company_id,location_id,product_id) do update set quantity=public.inventory.quantity+excluded.quantity,updated_at=clock_timestamp();
 end if;
 update public.inventory set quantity=case when p_action='count' then qty when p_action='receive' then quantity+qty else quantity-qty end,updated_at=clock_timestamp()
 where company_id=c and product_id=pid and location_id=lid;
 if p_action='sale' then
 insert into dpq.sales_ledger(id,company_id,product_id,location_id,quantity,kind,unit_price,unit_cost)
 select req,c,pid,lid,qty,'sale',sale_price,purchase_price from public.products where id=pid;
 end if;
 result:=jsonb_build_object('quantity',(select quantity from public.inventory where company_id=c and product_id=pid and location_id=lid),'unit_price',(select sale_price from public.products where id=pid),'total',qty*(select sale_price from public.products where id=pid));
 elsif p_action='channel_save' then
 if length(trim(coalesce(p_payload->>'name',''))) not between 1 and 100 then raise exception 'DPQ_INPUT: Kanal adı gerekli'; end if;
 ch:=coalesce(nullif(p_payload->>'channel_id','')::uuid,gen_random_uuid());
 if exists(select 1 from dpq.channels where id=ch and company_id<>c) then raise exception 'DPQ_ROLE: Başka şirket'; end if;
 insert into dpq.channels(id,company_id,name) values(ch,c,trim(p_payload->>'name'))
 on conflict(id) do update set name=excluded.name,active=true;
 delete from dpq.channel_locations where channel_id=ch;
 if jsonb_array_length(coalesce(p_payload->'locations','[]'))=0 then raise exception 'DPQ_INPUT: Satışa açık konum seçin'; end if;
 for item in select value from jsonb_array_elements(p_payload->'locations') loop
 lid:=(item->>'id')::uuid;
 if not exists(select 1 from public.locations where id=lid and company_id=c and active) then raise exception 'DPQ_LOCATION: Geçersiz konum'; end if;
 insert into dpq.channel_locations values(ch,lid,coalesce((item->>'buffer')::numeric,0));
 end loop;
 result:=jsonb_build_object('id',ch);
 elsif p_action='channel_archive' then
 update dpq.channels set active=false where id=(p_payload->>'channel_id')::uuid and company_id=c;
 if not found then raise exception 'DPQ_CHANNEL: Kanal yok'; end if;
 result:='{"archived":true}';
 elsif p_action='reserve' then
 ch:=(p_payload->>'channel_id')::uuid;
 if not exists(select 1 from dpq.channels where id=ch and company_id=c and active) then raise exception 'DPQ_CHANNEL: Etkin kanal gerekli'; end if;
 if length(trim(coalesce(p_payload->>'reference',''))) not between 1 and 100 or length(trim(coalesce(p_payload->>'customer',''))) not between 1 and 200 then raise exception 'DPQ_INPUT: Sipariş numarası ve müşteri gerekli'; end if;
 if p_payload->>'shipping'='consolidate' and conf.center_id is null then raise exception 'DPQ_CENTER: Merkez tanımlanmamış'; end if;
 if jsonb_array_length(coalesce(p_payload->'items','[]')) not between 1 and 100 then raise exception 'DPQ_INPUT: Sipariş satırları gerekli'; end if;
 insert into dpq.orders(company_id,channel_id,reference,customer,address,shipping,center_id,expires_at)
 values(c,ch,p_payload->>'reference',p_payload->>'customer',left(coalesce(p_payload->>'address',''),2000),p_payload->>'shipping',conf.center_id,clock_timestamp()+interval '30 minutes') returning id into oid;
 for item in select value from jsonb_array_elements(p_payload->'items') loop
 pid:=(item->>'product_id')::uuid; remaining:=(item->>'quantity')::numeric;
 if remaining is null or remaining='NaN'::numeric or remaining<=0 or remaining>1000000 or trunc(remaining)<>remaining or not exists(select 1 from public.products where id=pid and company_id=c and active) then raise exception 'DPQ_INPUT: Geçersiz sipariş satırı'; end if;
 for r in select l.id, greatest(0,dpq.available(c,pid,l.id)-cl.buffer) available
 from public.locations l join dpq.channel_locations cl on cl.location_id=l.id and cl.channel_id=ch
 where l.company_id=c and l.active
 order by (l.id=conf.center_id) desc, greatest(0,dpq.available(c,pid,l.id)-cl.buffer) desc,l.id loop
 take_qty:=least(remaining,r.available);
 if take_qty>0 then
 insert into dpq.allocations(order_id,product_id,location_id,quantity,unit_price,unit_cost)
 values(oid,pid,r.id,take_qty,(select sale_price from public.products where id=pid),(select purchase_price from public.products where id=pid));
 remaining:=remaining-take_qty;
 end if;
 exit when remaining=0;
 end loop;
 if remaining>0 then raise exception 'DPQ_STOCK: Sipariş için yeterli satılabilir stok yok'; end if;
 end loop;
 result:=jsonb_build_object('id',oid);
 elsif p_action in ('order_prepare','order_cancel','order_complete','allocation_dispatch','allocation_receive','allocation_ship','allocation_return') then
 oid:=(p_payload->>'order_id')::uuid;
 select * into ord from dpq.orders where id=oid and company_id=c;
 if not found then raise exception 'DPQ_ORDER: Sipariş bulunamadı'; end if;
 if p_action='order_prepare' then
 if not admin then raise exception 'DPQ_ROLE: Elle ödeme doğrulaması için yönetici gerekli'; end if;
 if ord.status<>'reserved' then raise exception 'DPQ_STATE: Sipariş rezervasyonda değil'; end if;
 -- Manual channel only. This is NOT a verified online payment notification.
 update dpq.orders set paid=true,status='preparing',expires_at=null where id=oid;
 elsif p_action='order_cancel' then
 if ord.status not in ('reserved','preparing') or exists(select 1 from dpq.allocations where order_id=oid and state in ('transit','shipped','returned')) then raise exception 'DPQ_STATE: Yolda/gönderilmiş sipariş doğrudan iptal edilemez'; end if;
 update dpq.allocations set state='released' where order_id=oid and state='reserved';
 update dpq.orders set status='cancelled' where id=oid;
 elsif p_action='order_complete' then
 if ord.status<>'shipped' then raise exception 'DPQ_STATE: Gönderim tamamlanmamış'; end if;
 update dpq.orders set status='completed' where id=oid;
 else
 select * into alloc from dpq.allocations where id=(p_payload->>'allocation_id')::uuid and order_id=oid;
 if not found then raise exception 'DPQ_ALLOCATION: Ayırma kaydı yok'; end if;
 if p_action='allocation_dispatch' then
 if ord.status<>'preparing' or ord.shipping<>'consolidate' or alloc.state<>'reserved' or alloc.location_id=ord.center_id then raise exception 'DPQ_STATE: Merkeze sevk edilemez'; end if;
 update public.inventory set quantity=quantity-alloc.quantity,updated_at=clock_timestamp() where company_id=c and product_id=alloc.product_id and location_id=alloc.location_id;
 update dpq.allocations set state='transit',target_id=ord.center_id where id=alloc.id;
 elsif p_action='allocation_receive' then
 if alloc.state<>'transit' then raise exception 'DPQ_STATE: Ürün yolda değil'; end if;
 insert into public.inventory(company_id,product_id,location_id,quantity) values(c,alloc.product_id,alloc.target_id,alloc.quantity)
 on conflict(company_id,location_id,product_id) do update set quantity=public.inventory.quantity+excluded.quantity,updated_at=clock_timestamp();
 update dpq.allocations set state='reserved',location_id=target_id,target_id=null where id=alloc.id;
 elsif p_action='allocation_ship' then
 if ord.status<>'preparing' or alloc.state<>'reserved' then raise exception 'DPQ_STATE: Gönderime hazır değil'; end if;
 if length(trim(coalesce(p_payload->>'carrier','')))=0 or length(trim(coalesce(p_payload->>'tracking','')))=0 then raise exception 'DPQ_INPUT: Kargo ve takip numarası gerekli'; end if;
 if ord.shipping='consolidate' and exists(select 1 from dpq.allocations where order_id=oid and (state='transit' or (state='reserved' and location_id<>ord.center_id))) then raise exception 'DPQ_STATE: Bütün ürünler merkeze ulaşmalı'; end if;
 update public.inventory set quantity=quantity-alloc.quantity,updated_at=clock_timestamp() where company_id=c and product_id=alloc.product_id and location_id=alloc.location_id;
 insert into dpq.sales_ledger values(req,c,alloc.product_id,alloc.location_id,alloc.quantity,'sale',alloc.unit_price,alloc.unit_cost,oid,clock_timestamp());
 update dpq.allocations set state='shipped',carrier=left(p_payload->>'carrier',100),tracking=left(p_payload->>'tracking',200) where id=alloc.id;
 if not exists(select 1 from dpq.allocations where order_id=oid and state in ('reserved','transit')) then update dpq.orders set status='shipped' where id=oid; end if;
 elsif p_action='allocation_return' then
 if not admin or alloc.state<>'shipped' then raise exception 'DPQ_STATE: Yönetici ve gönderilmiş ürün gerekli'; end if;
 if coalesce(p_payload->>'inspected','')<>'true' then raise exception 'DPQ_RETURN: Fiziksel teslim ve kontrol onayı gerekli'; end if;
 insert into public.inventory(company_id,product_id,location_id,quantity) values(c,alloc.product_id,alloc.location_id,alloc.quantity)
 on conflict(company_id,location_id,product_id) do update set quantity=public.inventory.quantity+excluded.quantity,updated_at=clock_timestamp();
 insert into dpq.sales_ledger values(req,c,alloc.product_id,alloc.location_id,alloc.quantity,'return',alloc.unit_price,alloc.unit_cost,oid,clock_timestamp());
 update dpq.allocations set state='returned' where id=alloc.id;
 end if;
 end if;
 result:=jsonb_build_object('id',oid,'updated',true);
 elsif p_action='catalog_product' then
 if length(trim(coalesce(p_payload->>'barcode','')))=0 or length(trim(coalesce(p_payload->>'name','')))=0 then raise exception 'DPQ_INPUT: Barkod ve ürün adı gerekli'; end if;
 if not coalesce((p_payload->>'sale_price')::numeric between 0 and 10000000 and (p_payload->>'purchase_price')::numeric between 0 and 10000000,false) then raise exception 'DPQ_INPUT: Geçersiz fiyat'; end if;
 insert into public.products(company_id,barcode,name,sale_price,purchase_price,critical_stock,active)
 values(c,trim(p_payload->>'barcode'),trim(p_payload->>'name'),(p_payload->>'sale_price')::numeric,(p_payload->>'purchase_price')::numeric,coalesce((p_payload->>'critical_stock')::numeric,0),true)
 on conflict(company_id,barcode) do update set name=excluded.name,sale_price=excluded.sale_price,purchase_price=excluded.purchase_price,critical_stock=excluded.critical_stock returning id into pid;
 result:=jsonb_build_object('id',pid);
 elsif p_action='catalog_location' then
 if length(trim(coalesce(p_payload->>'name','')))=0 or p_payload->>'type' not in ('center','warehouse','branch') then raise exception 'DPQ_INPUT: Geçersiz konum'; end if;
 insert into public.locations(company_id,name,location_type,active) values(c,trim(p_payload->>'name'),p_payload->>'type',true)
 on conflict(company_id,name) do update set active=true returning id into lid;
 result:=jsonb_build_object('id',lid);
 elsif p_action='device_disable' then
 if p_payload->>'code'=p_device then raise exception 'DPQ_DEVICE: Kullanılan cihaz burada kaldırılamaz'; end if;
 update dpq.devices set active=false where company_id=c and code=p_payload->>'code';
 result:='{"disabled":true}';
 elsif p_action='support' then
 if (select count(*) from dpq.tickets where actor=u and created_at>clock_timestamp()-interval '1 hour')>=10 then raise exception 'DPQ_RATE: Bir saatte en fazla 10 destek talebi'; end if;
 insert into dpq.tickets(company_id,actor,subject,message,contact) values(c,u,p_payload->>'subject',p_payload->>'message',p_payload->>'contact') returning id into oid;
 result:=jsonb_build_object('id',oid,'mail_status','pending');
 elsif p_action='renewal' then
 insert into dpq.renewal_preferences(company_id,renew) values(c,(p_payload->>'renew')::boolean)
 on conflict(company_id) do update set renew=excluded.renew,updated_at=clock_timestamp();
 result:=jsonb_build_object('renew',(p_payload->>'renew')::boolean,'valid_until',sub.valid_until);
 else raise exception 'DPQ_ACTION: Desteklenmeyen işlem';
 end if;
 insert into dpq.operations values(c,req,u,p_action,p_payload,result,clock_timestamp());
 insert into dpq.audit(company_id,actor,action,payload) values(c,u,p_action,p_payload);
 perform set_config('dpq.internal','',true);
 return result;
end $$;
revoke all on function public.dpq_call(text,jsonb,text) from public,anon;
grant execute on function public.dpq_call(text,jsonb,text) to authenticated;
revoke all on all functions in schema dpq from public,anon,authenticated;

-- 002_administration.sql
create table if not exists dpq.trial_claims (
 subject_hash text primary key, company_id uuid unique not null references public.companies(id),
 started_at timestamptz not null default now(), expires_at timestamptz not null default(now()+interval '30 days')
);
-- Called ONLY by the trusted enrollment service after identity/device checks.
-- Hash must be derived by the service, never accepted from a desktop payload.
create or replace function public.dpq_start_trial(p_company uuid,p_subject_hash text)
returns timestamptz language plpgsql security definer set search_path='' as $$
declare ending timestamptz;
begin
 if length(p_subject_hash)<32 then raise exception 'Verified enrollment identity required'; end if;
 insert into dpq.settings(company_id) values(p_company) on conflict do nothing;
 perform 1 from dpq.settings where company_id=p_company for update;
 if exists(select 1 from public.company_subscriptions where company_id=p_company) then raise exception 'Existing subscription must not be reset'; end if;
 insert into dpq.trial_claims(subject_hash,company_id) values(p_subject_hash,p_company) returning expires_at into ending;
 insert into public.company_subscriptions(company_id,status,valid_until,plan_code) values(p_company,'trial',ending,'demo');
 return ending;
end $$;
-- Enabling is deliberately a separate operation after inventory reconciliation.
create or replace function public.dpq_enable(p_company uuid,p_plan text,p_center uuid)
returns void language plpgsql security definer set search_path='' as $$
begin
 if not exists(select 1 from dpq.plans where code=p_plan) then raise exception 'Unknown plan'; end if;
 if not exists(select 1 from public.locations where id=p_center and company_id=p_company and active) then raise exception 'Invalid center'; end if;
 if not exists(select 1 from public.company_subscriptions where company_id=p_company) then raise exception 'Subscription missing'; end if;
 insert into dpq.settings(company_id) values(p_company) on conflict do nothing;
 perform 1 from dpq.settings where company_id=p_company for update;
 if exists(select 1 from dpq.settings where company_id=p_company and enabled) then raise exception 'Already enabled: use billing/admin plan change'; end if;
 update public.company_subscriptions set plan_code=p_plan,updated_at=clock_timestamp() where company_id=p_company;
 update dpq.settings set enabled=true,center_id=p_center where company_id=p_company;
end $$;
-- Trusted verified-payment adapter only. Exact match to server-created checkout.
create or replace function public.dpq_apply_payment(p_event text,p_order uuid,p_amount bigint,p_currency text)
returns jsonb language plpgsql security definer set search_path='' as $$
declare checkout dpq.checkout_orders%rowtype; previous dpq.payments%rowtype;
begin
 select * into checkout from dpq.checkout_orders where id=p_order;
 if not found then raise exception 'Unknown checkout'; end if;
 perform 1 from dpq.settings where company_id=checkout.company_id for update;
 select * into checkout from dpq.checkout_orders where id=p_order for update;
 if p_event is null or length(p_event) not between 1 and 200 or p_amount is distinct from checkout.amount_minor or p_currency is distinct from checkout.currency then raise exception 'Payment mismatch'; end if;
 select * into previous from dpq.payments where provider_event=p_event;
 if found then
 if previous.order_id<>p_order::text then raise exception 'Event replay mismatch'; end if;
 return '{"applied":true,"duplicate":true}';
 end if;
 if checkout.paid then return '{"applied":true,"duplicate":true}'; end if;
 if checkout.period_end<=clock_timestamp() then raise exception 'Stale checkout requires reconciliation'; end if;
 insert into dpq.payments(provider_event,company_id,order_id,amount_minor,currency,plan,period_end)
 values(p_event,checkout.company_id,p_order::text,p_amount,p_currency,checkout.plan,checkout.period_end);
 update dpq.checkout_orders set paid=true where id=p_order;
 -- Never shorten paid entitlement. Suspended accounts require staff review.
 if exists(select 1 from public.company_subscriptions where company_id=checkout.company_id and status='suspended') then raise exception 'Suspended account: manual reconciliation required'; end if;
 update public.company_subscriptions set status='active',plan_code=checkout.plan,
 valid_until=greatest(valid_until,checkout.period_end),updated_at=clock_timestamp() where company_id=checkout.company_id;
 if not found then raise exception 'Subscription missing'; end if;
 return '{"applied":true,"duplicate":false}';
end $$;
revoke all on table dpq.trial_claims from public,anon,authenticated;
revoke all on function public.dpq_start_trial(uuid,text),public.dpq_enable(uuid,text,uuid),public.dpq_apply_payment(text,uuid,bigint,text) from public,anon,authenticated;
grant execute on function public.dpq_start_trial(uuid,text),public.dpq_enable(uuid,text,uuid),public.dpq_apply_payment(text,uuid,bigint,text) to service_role;

-- 003_support.sql
alter table dpq.tickets add column if not exists attempts integer not null default 0;
alter table dpq.tickets add column if not exists available_at timestamptz not null default now();
alter table dpq.tickets add column if not exists lease uuid;
create or replace function public.dpq_claim_support() returns jsonb
language plpgsql security definer set search_path='' as $$
declare ticket dpq.tickets%rowtype; token uuid:=gen_random_uuid();
begin
 select * into ticket from dpq.tickets where mail_status<>'sent' and available_at<=clock_timestamp() and attempts<10
 order by created_at for update skip locked limit 1;
 if not found then return null; end if;
 update dpq.tickets set lease=token,attempts=attempts+1,available_at=clock_timestamp()+interval '5 minutes' where id=ticket.id;
 return to_jsonb(ticket)||jsonb_build_object('lease',token);
end $$;
create or replace function public.dpq_finish_support(p_ticket uuid,p_lease uuid,p_sent boolean) returns boolean
language plpgsql security definer set search_path='' as $$
begin
 update dpq.tickets set mail_status=case when p_sent then 'sent' else 'failed' end,
 available_at=clock_timestamp()+interval '15 minutes',lease=null where id=p_ticket and lease=p_lease;
 return found;
end $$;
revoke all on function public.dpq_claim_support(),public.dpq_finish_support(uuid,uuid,boolean) from public,anon,authenticated;
grant execute on function public.dpq_claim_support(),public.dpq_finish_support(uuid,uuid,boolean) to service_role;

-- 004_access.sql
-- Existing restrictive subscription policy remains. This adds strict paid-period expiry
-- for migrated companies; no grace-period bypass through old REST clients.
create or replace function public.dpq_read_allows(p_company uuid) returns boolean
language sql stable security definer set search_path='' as $$
 select exists(select 1 from public.company_members where company_id=p_company and user_id=auth.uid() and active)
 and (not exists(select 1 from dpq.settings where company_id=p_company and enabled)
 or exists(select 1 from public.company_subscriptions s join dpq.plans p on p.code=s.plan_code
 where s.company_id=p_company and s.status in ('trial','active','past_due') and s.valid_until>now()))
$$;
revoke all on function public.dpq_read_allows(uuid) from public,anon;
grant execute on function public.dpq_read_allows(uuid) to authenticated;
do $$ declare t text; begin
 foreach t in array array['locations','products','inventory','stock_movements','cloud_devices','cloud_operations','sync_events','product_change_requests'] loop
 if to_regclass('public.'||t) is not null then
 execute format('drop policy if exists dpq_strict_subscription on public.%I',t);
 execute format('create policy dpq_strict_subscription on public.%I as restrictive for all to authenticated using(public.dpq_read_allows(company_id)) with check(public.dpq_read_allows(company_id))',t);
 end if;
 end loop;
end $$;
commit;
