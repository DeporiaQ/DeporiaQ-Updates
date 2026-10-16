-- DeporiaQ 0.24.1: existing 0.24.0 installation required. Preserves subscriptions.
begin;
create table if not exists dpq.counter_orders (
 id uuid primary key, company_id uuid not null references public.companies(id),
 actor uuid not null, origin_id uuid not null references public.locations(id),
 location_id uuid not null references public.locations(id), product_id uuid not null references public.products(id),
 quantity numeric not null check(quantity>0 and trunc(quantity)=quantity),
 unit_price numeric not null, unit_cost numeric not null,
 delivery text not null check(delivery in ('pickup','cargo')),
 customer text not null, contact text not null, address text not null default '',
 status text not null default 'reserved' check(status in ('reserved','shipped','completed','cancelled','expired')),
 carrier text not null default '', tracking text not null default '',
 created_at timestamptz not null default now(), expires_at timestamptz not null
);
alter table dpq.counter_orders enable row level security;
revoke all on dpq.counter_orders from public,anon,authenticated;
create or replace function dpq.available(c uuid,p uuid,l uuid) returns numeric
language sql stable set search_path='' as $$
 select coalesce((select quantity from public.inventory where company_id=c and product_id=p and location_id=l),0)
 - coalesce((select sum(a.quantity) from dpq.allocations a join dpq.orders o on o.id=a.order_id
 where o.company_id=c and a.product_id=p and a.location_id=l and a.state='reserved'),0)
 - coalesce((select sum(quantity) from dpq.counter_orders where company_id=c and product_id=p and location_id=l
 and status='reserved' and expires_at>statement_timestamp()),0)
$$;
create or replace function public.dpq_call(p_action text,p_payload jsonb default '{}',p_device text default '')
returns jsonb language plpgsql security definer set search_path='' as $$
declare
 c uuid; u uuid:=auth.uid(); role_name text; conf dpq.settings%rowtype; sub public.company_subscriptions%rowtype;
 max_devices integer; allowed boolean; enabled boolean; oid uuid; pid uuid; lid uuid; target uuid; ch uuid;
 qty numeric; remaining numeric; take_qty numeric; result jsonb; req uuid; prior dpq.operations%rowtype;
 r record; item jsonb; alloc dpq.allocations%rowtype; ord dpq.orders%rowtype; admin boolean; counter_order dpq.counter_orders%rowtype;
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
 update dpq.counter_orders set status='expired' where company_id=c and status='reserved' and expires_at<=clock_timestamp();
 if p_action='snapshot' then
 return jsonb_build_object(
 'sale_locations',coalesce((select jsonb_agg(l.id) from public.locations l where l.company_id=c and l.active and (admin or exists(select 1 from dpq.staff_locations x where x.company_id=c and x.user_id=u and x.location_id=l.id))),'[]'),
 'counter_orders',coalesce((select jsonb_agg(to_jsonb(o) order by o.created_at desc) from dpq.counter_orders o where o.company_id=c and (admin or o.actor=u or exists(select 1 from dpq.staff_locations x where x.company_id=c and x.user_id=u and x.location_id=o.location_id))),'[]'),
 'products',coalesce((select jsonb_agg(to_jsonb(p)) from public.products p where company_id=c),'[]'),
 'locations',coalesce((select jsonb_agg(to_jsonb(l)) from public.locations l where company_id=c),'[]'),
 'inventory',coalesce((select jsonb_agg(to_jsonb(i)||jsonb_build_object('available',dpq.available(c,i.product_id,i.location_id))) from public.inventory i where company_id=c),'[]'),
 'sales',coalesce((select jsonb_agg(to_jsonb(e)) from dpq.sales_ledger e where company_id=c and admin),'[]'),
 'channels',coalesce((select jsonb_agg(to_jsonb(x)) from dpq.channels x where company_id=c),'[]'),
 'orders',coalesce((select jsonb_agg(to_jsonb(o)||jsonb_build_object('allocations',coalesce((select jsonb_agg(to_jsonb(a)) from dpq.allocations a where a.order_id=o.id),'[]'))) from dpq.orders o where company_id=c and admin),'[]'));
 end if;
 if p_action not in ('support','renewal') and role_name not in ('owner','admin','manager','employee','warehouse','branch') then raise exception 'DPQ_ROLE: Salt okunur hesap'; end if;
 if p_action in ('channel_save','channel_archive','catalog_product','catalog_location','count','receive','device_disable','renewal') and not admin then raise exception 'DPQ_ROLE: Yönetici gerekli'; end if;
 if not admin and p_action not in ('sale','transfer','support','counter_reserve','counter_collect','counter_ship','counter_complete','counter_cancel') then
 raise exception 'DPQ_ROLE: Bu aday sürümde sipariş yönetimi yetkili işletme yöneticisine açıktır'; end if;
 if not admin and p_action in ('sale','transfer','counter_reserve') then
 if not exists(select 1 from dpq.staff_locations where company_id=c and user_id=u and location_id=(p_payload->>'location_id')::uuid) then
 raise exception 'DPQ_LOCATION_ROLE: Bu konumda işlem yetkiniz yok'; end if;
 if p_action in ('sale','counter_reserve') and role_name not in ('branch','employee','manager') then raise exception 'DPQ_ROLE: Satış yetkisi yok'; end if;
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
 elsif p_action='counter_reserve' then
 if pid is null or lid is null or target is null or qty is null or qty='NaN'::numeric or qty<=0 or qty>1000000 or trunc(qty)<>qty then raise exception 'DPQ_INPUT: Geçersiz ürün, konum veya adet'; end if;
 if not coalesce(p_payload->>'delivery' in ('pickup','cargo'),false)
 or length(trim(coalesce(p_payload->>'customer',''))) not between 2 and 200
 or length(trim(coalesce(p_payload->>'contact',''))) not between 3 and 300
 or (p_payload->>'delivery'='cargo' and length(trim(coalesce(p_payload->>'address',''))) not between 5 and 1000)
 then raise exception 'DPQ_INPUT: Müşteri, iletişim ve teslimat bilgileri gerekli'; end if;
 if dpq.available(c,pid,target)<qty then raise exception 'DPQ_STOCK: Seçili şube / depoda satılabilir stok yetersiz'; end if;
 insert into dpq.counter_orders(id,company_id,actor,origin_id,location_id,product_id,quantity,unit_price,unit_cost,delivery,customer,contact,address,expires_at)
 select req,c,u,lid,target,pid,qty,sale_price,purchase_price,p_payload->>'delivery',trim(p_payload->>'customer'),trim(p_payload->>'contact'),coalesce(p_payload->>'address',''),clock_timestamp()+interval '24 hours'
 from public.products where id=pid;
 select to_jsonb(o) into result from dpq.counter_orders o where id=req;
 elsif p_action in ('counter_collect','counter_ship','counter_complete','counter_cancel') then
 select * into counter_order from dpq.counter_orders where id=(p_payload->>'order_id')::uuid and company_id=c for update;
 if not found then raise exception 'DPQ_ORDER: Rezervasyon bulunamadı'; end if;
 if not admin then
 if role_name not in ('branch','employee','manager','warehouse') then raise exception 'DPQ_ROLE: Teslimat yetkisi yok'; end if;
 if not exists(select 1 from dpq.staff_locations where company_id=c and user_id=u and location_id=counter_order.location_id)
 and not (p_action='counter_cancel' and counter_order.actor=u) then raise exception 'DPQ_LOCATION_ROLE: Teslim konumunda işlem yetkiniz yok'; end if;
 end if;
 if p_action='counter_cancel' then
 if counter_order.status<>'reserved' then raise exception 'DPQ_STATE: Yalnız bekleyen rezervasyon iptal edilebilir'; end if;
 update dpq.counter_orders set status='cancelled' where id=counter_order.id;
 elsif p_action='counter_complete' then
 if counter_order.status<>'shipped' then raise exception 'DPQ_STATE: Kargoya verilmiş rezervasyon gerekli'; end if;
 update dpq.counter_orders set status='completed' where id=counter_order.id;
 else
 if counter_order.status<>'reserved' or counter_order.expires_at<=clock_timestamp() then raise exception 'DPQ_STATE: Rezervasyon etkin değil'; end if;
 if (p_action='counter_collect' and counter_order.delivery<>'pickup') or (p_action='counter_ship' and counter_order.delivery<>'cargo') then raise exception 'DPQ_STATE: Teslimat türü uyuşmuyor'; end if;
 if not coalesce((p_payload->>'paid')::boolean,false) then raise exception 'DPQ_PAYMENT: Ödeme doğrulaması gerekli'; end if;
 if p_action='counter_ship' and (length(trim(coalesce(p_payload->>'carrier',''))) not between 1 and 100 or length(trim(coalesce(p_payload->>'tracking',''))) not between 1 and 200) then raise exception 'DPQ_INPUT: Kargo firması ve takip numarası gerekli'; end if;
 update public.inventory set quantity=quantity-counter_order.quantity,updated_at=clock_timestamp()
 where company_id=c and product_id=counter_order.product_id and location_id=counter_order.location_id and quantity>=counter_order.quantity;
 if not found then raise exception 'DPQ_STOCK: Fiziksel stok yetersiz'; end if;
 insert into dpq.sales_ledger(id,company_id,product_id,location_id,quantity,kind,unit_price,unit_cost)
 values(req,c,counter_order.product_id,counter_order.location_id,counter_order.quantity,'sale',counter_order.unit_price,counter_order.unit_cost);
 update dpq.counter_orders set status=case when p_action='counter_ship' then 'shipped' else 'completed' end,
 carrier=coalesce(p_payload->>'carrier',''),tracking=coalesce(p_payload->>'tracking','') where id=counter_order.id;
 end if;
 select to_jsonb(o) into result from dpq.counter_orders o where id=counter_order.id;
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
revoke all on function dpq.available(uuid,uuid,uuid) from public,anon,authenticated;
revoke all on function public.dpq_call(text,jsonb,text) from public,anon;
grant execute on function public.dpq_call(text,jsonb,text) to authenticated;
commit;
