-- 0.28 retail workspaces. Additive; never changes subscriptions or invents stock.
begin;
create table if not exists dpq.retail_grants (
 company_id uuid not null references public.companies(id),user_id uuid not null,device text not null,
 capability text not null check(capability in ('offers','layout','finance','customers')),
 primary key(company_id,user_id,device,capability)
);
create table if not exists dpq.retail_offers (
 company_id uuid not null references public.companies(id),id uuid not null default gen_random_uuid(),
 kind text not null check(kind in ('campaign','bundle')),name text not null,items jsonb not null,
 discount numeric(5,2) not null check(discount>0 and discount<100),starts_at timestamptz not null,ends_at timestamptz not null,
 member_only boolean not null default false,location_ids jsonb not null default '[]',active boolean not null default true,
 version integer not null default 1,actor uuid not null,updated_at timestamptz not null default now(),
 primary key(company_id,id),check(ends_at>starts_at)
);
create table if not exists dpq.retail_customers (
 company_id uuid not null references public.companies(id),id uuid not null default gen_random_uuid(),
 name text not null,phone text not null default '',email text not null default '',member boolean not null default false,
 email_consent boolean not null default false,sms_consent boolean not null default false,
 consent_note text not null default '',consent_at timestamptz,active boolean not null default true,
 version integer not null default 1,actor uuid not null,updated_at timestamptz not null default now(),primary key(company_id,id)
);
create table if not exists dpq.retail_consent_history (
 company_id uuid not null,customer_id uuid not null,actor uuid not null,recorded_at timestamptz not null default now(),
 member boolean not null,email_consent boolean not null,sms_consent boolean not null,evidence text not null,
 foreign key(company_id,customer_id) references dpq.retail_customers(company_id,id)
);
create table if not exists dpq.retail_sale_links (
 company_id uuid not null,sale_id uuid primary key references dpq.sales_ledger(id),receipt_id uuid not null,
 channel_id uuid references dpq.channels(id),customer_id uuid,original_sale_id uuid references dpq.sales_ledger(id),
 offer_id uuid,foreign key(company_id,customer_id) references dpq.retail_customers(company_id,id)
);
create index if not exists retail_sale_receipt on dpq.retail_sale_links(company_id,receipt_id);
create index if not exists retail_sale_original on dpq.retail_sale_links(company_id,original_sale_id);
create table if not exists dpq.retail_expenses (
 company_id uuid not null,id uuid not null default gen_random_uuid(),location_id uuid references public.locations(id),
 channel_id uuid references dpq.channels(id),name text not null,amount numeric(16,2) not null check(amount>0),
 incurred_on date not null,active boolean not null default true,actor uuid not null,primary key(company_id,id)
);
create table if not exists dpq.rack_layouts (
 company_id uuid not null references public.companies(id),location_id uuid not null references public.locations(id),
 spec jsonb not null,version integer not null default 1,actor uuid not null,updated_at timestamptz not null default now(),
 primary key(company_id,location_id)
);
create table if not exists dpq.rack_stock (
 company_id uuid not null,location_id uuid not null,rack text not null,level integer not null check(level>0),
 product_id uuid not null references public.products(id),quantity integer not null check(quantity>0),
 unit_width numeric(8,2) not null check(unit_width>0),verified boolean not null default false,
 primary key(company_id,location_id,rack,level,product_id),
 foreign key(company_id,location_id) references dpq.rack_layouts(company_id,location_id)
);
create index if not exists rack_stock_product on dpq.rack_stock(company_id,product_id,location_id);
create index if not exists retail_ledger_period on dpq.sales_ledger(company_id,created_at,location_id);
do $$ declare t text; begin
 foreach t in array array['retail_grants','retail_offers','retail_customers','retail_consent_history','retail_sale_links','retail_expenses','rack_layouts','rack_stock'] loop
 execute format('alter table dpq.%I enable row level security',t);
 execute format('revoke all on dpq.%I from public,anon,authenticated',t);
 end loop;
end $$;

create or replace function dpq.retail_finance(c uuid,p jsonb) returns jsonb
language plpgsql security invoker set search_path='' as $$
declare first_day date:=(p->>'from')::date;last_day date:=(p->>'to')::date;
 lid uuid:=nullif(p->>'location_id','')::uuid;channel uuid:=nullif(p->>'channel_id','')::uuid;data jsonb;expenses jsonb;totals jsonb;
begin
 if first_day is null or last_day is null or last_day<first_day or last_day-first_day>3660 then raise exception 'DPQ_INPUT: Geçerli tarih aralığı seçin';end if;
 with ledger as (
 select s.*,coalesce(k.channel_id,o.channel_id) channel,
 case when s.kind='return' then -1 else 1 end sign
 from dpq.sales_ledger s left join dpq.retail_sale_links k on k.company_id=c and k.sale_id=s.id
 left join dpq.orders o on o.company_id=c and o.id=s.order_id
 where s.company_id=c and s.created_at>=first_day::timestamp at time zone 'Europe/Istanbul'
 and s.created_at<(last_day+1)::timestamp at time zone 'Europe/Istanbul'
 and (lid is null or s.location_id=lid) and (channel is null or coalesce(k.channel_id,o.channel_id)=channel))
 select jsonb_build_object('sales',coalesce(sum(quantity*unit_price) filter(where kind='sale'),0),
 'returns',coalesce(sum(quantity*unit_price) filter(where kind='return'),0),
 'revenue',coalesce(sum(sign*quantity*unit_price),0),'cost',coalesce(sum(sign*quantity*unit_cost),0),
 'units',coalesce(sum(sign*quantity),0),'missing_cost_lines',count(*) filter(where unit_cost=0)) into totals from ledger;
 with ledger as (
 select s.*,coalesce(k.channel_id,o.channel_id) channel,case when s.kind='return' then -1 else 1 end sign
 from dpq.sales_ledger s left join dpq.retail_sale_links k on k.company_id=c and k.sale_id=s.id
 left join dpq.orders o on o.company_id=c and o.id=s.order_id
 where s.company_id=c and s.created_at>=first_day::timestamp at time zone 'Europe/Istanbul'
 and s.created_at<(last_day+1)::timestamp at time zone 'Europe/Istanbul'
 and (lid is null or s.location_id=lid) and (channel is null or coalesce(k.channel_id,o.channel_id)=channel)),
 grouped as (select (s.created_at at time zone 'Europe/Istanbul')::date as period,s.location_id,s.channel,
 sum(sign*quantity*unit_price) revenue,sum(sign*quantity*unit_cost) cost,sum(sign*quantity) units
 from ledger s group by 1,2,3)
 select coalesce(jsonb_agg(to_jsonb(g)||jsonb_build_object('location',l.name,'channel_name',coalesce(ch.name,'Mağaza / Doğrudan')) order by g.period desc,l.name),'[]') into data
 from grouped g join public.locations l on l.company_id=c and l.id=g.location_id left join dpq.channels ch on ch.company_id=c and ch.id=g.channel;
 select coalesce(jsonb_agg(to_jsonb(e) order by incurred_on desc),'[]') into expenses from dpq.retail_expenses e
 where company_id=c and active and incurred_on between first_day and last_day and (lid is null or location_id=lid) and (channel is null or channel_id=channel);
 return jsonb_build_object('totals',totals||jsonb_build_object('expenses',(select coalesce(sum((x->>'amount')::numeric),0) from jsonb_array_elements(expenses) x)),
 'rows',data,'expenses',expenses,'from',first_day,'to',last_day,'timezone','Europe/Istanbul');
end $$;

create or replace function dpq.retail_can(c uuid,u uuid,d text,r text,cap text) returns boolean
language sql stable security invoker set search_path='' as $$
 select r='owner' or (r='admin' and cap in ('layout','finance','customers')) or exists(
 select 1 from dpq.retail_grants where company_id=c and user_id=u and device=d and capability=cap)
$$;

create or replace function dpq.retail_quote(c uuid,u uuid,d text,r text,p jsonb) returns jsonb
language plpgsql security invoker set search_path='' as $$
declare lid uuid:=(p->>'location_id')::uuid;cid uuid:=nullif(p->>'customer_id','')::uuid;
 channel uuid:=nullif(p->>'channel_id','')::uuid;member_ok boolean:=false;item jsonb;part jsonb;parts jsonb;
 offer dpq.retail_offers%rowtype;product public.products%rowtype;pid uuid;bid uuid;qty numeric;units numeric;
 discount numeric;price numeric;total numeric:=0;cost_total numeric:=0;lines jsonb:='[]';available numeric;quote jsonb;
begin
 if not exists(select 1 from public.locations where company_id=c and id=lid and active) then raise exception 'DPQ_LOCATION: Etkin konum seçin';end if;
 if r not in ('owner','admin') and not exists(select 1 from dpq.staff_locations where company_id=c and user_id=u and location_id=lid) then raise exception 'DPQ_LOCATION_ROLE: Bu konumda satış yetkiniz yok';end if;
 if channel is not null and not exists(select 1 from dpq.channels where company_id=c and id=channel and active) then raise exception 'DPQ_CHANNEL: Etkin satış kanalı seçin';end if;
 if cid is not null then
 select member into member_ok from dpq.retail_customers where company_id=c and id=cid and active;
 if not found then raise exception 'DPQ_CUSTOMER: Müşteri kaydını yenileyin';end if;
 end if;
 if jsonb_typeof(p->'items') is distinct from 'array' or jsonb_array_length(p->'items') not between 1 and 200 then raise exception 'DPQ_INPUT: Sepete ürün ekleyin';end if;
 for item in select value from jsonb_array_elements(p->'items') loop
 qty:=(item->>'quantity')::numeric;
 if qty is null or qty<>trunc(qty) or qty not between 1 and 1000000 then raise exception 'DPQ_INPUT: Tam sayı adet gerekli';end if;
 bid:=nullif(item->>'bundle_id','')::uuid;offer:=null;
 if bid is not null then
 select * into offer from dpq.retail_offers where company_id=c and id=bid and kind='bundle' and active
 and starts_at<=clock_timestamp() and ends_at>clock_timestamp() and (not member_only or member_ok)
 and (location_ids='[]'::jsonb or location_ids ? lid::text);
 if not found then raise exception 'DPQ_OFFER: Set etkin değil veya bu müşteri/konum için uygun değil';end if;
 parts:=offer.items;
 else
 parts:=jsonb_build_array(jsonb_build_object('product_id',item->>'product_id','quantity',1));
 end if;
 for part in select value from jsonb_array_elements(parts) loop
 pid:=(part->>'product_id')::uuid;units:=qty*(part->>'quantity')::numeric;
 if units is null or units not between 1 and 1000000 then raise exception 'DPQ_INPUT: Set adedi sınırı aşıldı';end if;
 select * into product from public.products where company_id=c and id=pid and active;
 if not found then raise exception 'DPQ_PRODUCT: Etkin ürün bulunamadı';end if;
 if bid is null then
 select o.* into offer from dpq.retail_offers o where o.company_id=c and o.kind='campaign' and o.active
 and o.starts_at<=clock_timestamp() and o.ends_at>clock_timestamp() and (not o.member_only or member_ok)
 and (o.location_ids='[]'::jsonb or o.location_ids ? lid::text)
 and exists(select 1 from jsonb_array_elements(o.items) i where i->>'product_id'=pid::text)
 order by o.discount desc,o.id limit 1;
 end if;
 discount:=coalesce(offer.discount,0);price:=round(product.sale_price*(1-discount/100),2);
 if price<product.purchase_price then raise exception 'DPQ_COST: Satış fiyatı güncel maliyetin altında; fiyat veya kampanyayı düzeltin';end if;
 lines:=lines||jsonb_build_array(jsonb_build_object('product_id',pid,'barcode',product.barcode,'name',product.name,
 'quantity',units,'price',price,'cost',product.purchase_price,'discount',discount,'offer_id',offer.id,'offer_version',offer.version,'bundle_id',bid));
 total:=total+price*units;cost_total:=cost_total+product.purchase_price*units;
 end loop;
 end loop;
 if jsonb_array_length(lines)>1000 then raise exception 'DPQ_INPUT: Sepet en fazla 1000 ürün satırı içerebilir';end if;
 for part in select jsonb_build_object('id',x->>'product_id','qty',sum((x->>'quantity')::numeric))
 from jsonb_array_elements(lines) x group by x->>'product_id' loop
 available:=dpq.available(c,(part->>'id')::uuid,lid);
 if available<(part->>'qty')::numeric then raise exception 'DPQ_STOCK: Seçili şube veya depoda ayrılabilir stok yetersiz';end if;
 end loop;
 quote:=jsonb_build_object('location_id',lid,'channel_id',channel,'customer_id',cid,'lines',lines,'total',total);
 quote:=quote||jsonb_build_object('fingerprint',md5(quote::text),'cost',cost_total,'gross_profit',total-cost_total);
 if not dpq.retail_can(c,u,d,r,'finance') then
 select jsonb_agg(x-'cost') into lines from jsonb_array_elements(lines) x;
 quote:=(quote-'cost'-'gross_profit')||jsonb_build_object('lines',lines);
 end if;
 return quote;
end $$;

-- A legacy stock movement cannot leave more books on shelves than in stock.
-- New arrivals stay unplaced until located; inferred reductions require checking.
create or replace function dpq.rack_reconcile() returns trigger
language plpgsql security definer set search_path='' as $$
declare excess numeric;s record;n integer;
begin
 if tg_op='UPDATE' and new.quantity>=old.quantity then return new;end if;
 select coalesce(sum(quantity),0)-case when tg_op='DELETE' then 0 else new.quantity end into excess
 from dpq.rack_stock where company_id=old.company_id and location_id=old.location_id and product_id=old.product_id;
 for s in select * from dpq.rack_stock where company_id=old.company_id and location_id=old.location_id and product_id=old.product_id order by verified,rack,level for update loop
 exit when excess<=0;n:=least(excess,s.quantity);
 if n=s.quantity then delete from dpq.rack_stock where company_id=s.company_id and location_id=s.location_id and rack=s.rack and level=s.level and product_id=s.product_id;
 else update dpq.rack_stock set quantity=quantity-n,verified=false where company_id=s.company_id and location_id=s.location_id and rack=s.rack and level=s.level and product_id=s.product_id;end if;
 excess:=excess-n;
 end loop;
 if tg_op='DELETE' then return old;end if;return new;
end $$;
drop trigger if exists dpq_rack_reconcile on public.inventory;
create trigger dpq_rack_reconcile after update or delete on public.inventory for each row execute function dpq.rack_reconcile();

create or replace function dpq.retail_layout(c uuid,u uuid,op text,p jsonb) returns jsonb
language plpgsql security invoker set search_path='' as $$
declare lid uuid:=(p->>'location_id')::uuid;old dpq.rack_layouts%rowtype;spec jsonb:=p->'spec';rack_spec jsonb;s record;
 pid uuid;qty integer;wid numeric;lev integer;rid text;used numeric;stock numeric;result jsonb;
begin
 if not exists(select 1 from public.locations where company_id=c and id=lid and active) then raise exception 'DPQ_LOCATION: Etkin konum gerekli';end if;
 select * into old from dpq.rack_layouts where company_id=c and location_id=lid for update;
 if old.version is not null and old.version<>coalesce((p->>'version')::integer,0) then raise exception 'DPQ_CONFLICT: Raf planı değişti; yenileyin';end if;
 if op='save' then
 if jsonb_typeof(spec->'racks') is distinct from 'array' or jsonb_array_length(spec->'racks') not between 1 and 200 then raise exception 'DPQ_LAYOUT: 1–200 raf tanımlayın';end if;
 if coalesce((spec->>'bay_gap')::numeric,16) not between 0 and 500 then raise exception 'DPQ_LAYOUT: Raf aralığı 0–500 cm olmalı';end if;
 if (spec->>'aisle')::numeric is null or (spec->>'aisle')::numeric not between 60 and 1000 then raise exception 'DPQ_LAYOUT: Koridor genişliği 60–1000 cm olmalı';end if;
 for rack_spec in select value from jsonb_array_elements(spec->'racks') loop
 if coalesce(rack_spec->>'id','') !~ '^[A-Za-z0-9_-]{1,40}$' or (rack_spec->>'row')::integer is null or (rack_spec->>'row')::integer not between 1 and 30
 or (rack_spec->>'bay')::integer is null or (rack_spec->>'bay')::integer not between 1 and 30
 or (rack_spec->>'levels')::integer is null or (rack_spec->>'levels')::integer not between 1 and 10
 or (rack_spec->>'width')::numeric is null or (rack_spec->>'width')::numeric not between 20 and 1000
 or (rack_spec->>'depth')::numeric is null or (rack_spec->>'depth')::numeric not between 10 and 500
 or (rack_spec->>'height')::numeric is null or (rack_spec->>'height')::numeric not between 50 and 1000
 then raise exception 'DPQ_LAYOUT: Raf ölçüleri veya numaraları geçersiz';end if;
 end loop;
 if exists(select 1 from jsonb_array_elements(spec->'racks') r group by r->>'id' having count(*)>1)
 or exists(select 1 from jsonb_array_elements(spec->'racks') r group by r->>'row',r->>'bay' having count(*)>1) then raise exception 'DPQ_LAYOUT: Raf numarası veya sıra konumu yinelenemez';end if;
 for s in select rack,level,sum(quantity*unit_width) width from dpq.rack_stock where company_id=c and location_id=lid group by rack,level loop
 select x into rack_spec from jsonb_array_elements(spec->'racks') x where x->>'id'=s.rack;
 if rack_spec is null or (rack_spec->>'levels')::integer<s.level or (rack_spec->>'width')::numeric<s.width then raise exception 'DPQ_SHELF_FULL: Dolu rafı kaldırmadan veya daraltmadan önce ürünleri taşıyın';end if;
 end loop;
 insert into dpq.rack_layouts(company_id,location_id,spec,actor) values(c,lid,spec,u)
 on conflict(company_id,location_id) do update set spec=excluded.spec,version=dpq.rack_layouts.version+1,updated_at=clock_timestamp();
 elsif op='place' then
 rid:=p->>'rack';lev:=(p->>'level')::integer;pid:=(p->>'product_id')::uuid;qty:=(p->>'quantity')::integer;wid:=(p->>'unit_width')::numeric;
 if qty is null or (p->>'quantity')::numeric<>qty or qty not between 0 and 1000000 or wid is null or wid not between .1 and 1000 then raise exception 'DPQ_INPUT: Adet ve ürün genişliği geçersiz';end if;
 select x into rack_spec from jsonb_array_elements(old.spec->'racks') x where x->>'id'=rid;
 if rack_spec is null or lev is null or lev not between 1 and (rack_spec->>'levels')::integer then raise exception 'DPQ_LAYOUT: Raf veya kat bulunamadı';end if;
 if not exists(select 1 from public.products where company_id=c and id=pid and active) then raise exception 'DPQ_PRODUCT: Etkin ürün gerekli';end if;
 select coalesce(sum(quantity),0) into used from dpq.rack_stock where company_id=c and location_id=lid and product_id=pid and not(rack=rid and level=lev);
 select quantity into stock from public.inventory where company_id=c and location_id=lid and product_id=pid;
 if used+qty>coalesce(stock,0) then raise exception 'DPQ_STOCK: Yerleştirilen adet konum stoğunu aşıyor';end if;
 select coalesce(sum(quantity*unit_width),0) into used from dpq.rack_stock where company_id=c and location_id=lid and rack=rid and level=lev and product_id<>pid;
 if used+qty*wid>(rack_spec->>'width')::numeric then raise exception 'DPQ_SHELF_FULL: Bu katta yeterli boş genişlik yok';end if;
 delete from dpq.rack_stock where company_id=c and location_id=lid and rack=rid and level=lev and product_id=pid;
 if qty>0 then insert into dpq.rack_stock values(c,lid,rid,lev,pid,qty,wid,coalesce((p->>'verified')::boolean,false));end if;
 update dpq.rack_layouts set version=version+1,updated_at=clock_timestamp() where company_id=c and location_id=lid;
 else raise exception 'DPQ_ACTION: Bilinmeyen raf işlemi';end if;
 select to_jsonb(x) into result from dpq.rack_layouts x where company_id=c and location_id=lid;return result;
end $$;

create or replace function dpq.retail_seed(c uuid,u uuid) returns integer
language plpgsql security invoker set search_path='' as $$
declare loc record;prod record;spec jsonb;rr integer;bb integer;ll integer;bays integer;n integer:=0;
 qty integer;take integer;remaining integer;slot integer;slot_count integer;counts integer[];rackid text;
begin
 for loc in select l.id,coalesce(sum(i.quantity),0) qty from public.locations l left join public.inventory i on i.company_id=l.company_id and i.location_id=l.id
 where l.company_id=c and l.active and not exists(select 1 from dpq.rack_layouts x where x.company_id=c and x.location_id=l.id) group by l.id loop
 bays:=least(20,greatest(2,ceil(loc.qty/1200.0)::integer));spec:='[]';
 for rr in 1..3 loop for bb in 1..bays loop
 spec:=spec||jsonb_build_array(jsonb_build_object('id','R'||rr||'-B'||bb,'row',rr,'bay',bb,'levels',5,'width',160,'depth',50,'height',220));
 end loop;end loop;
 insert into dpq.rack_layouts(company_id,location_id,spec,actor) values(c,loc.id,jsonb_build_object('aisle',140,'racks',spec,'proposed',true),u);
 slot_count:=3*bays*5;counts:=array_fill(80,array[slot_count]);slot:=1;
 for prod in select i.product_id,i.quantity from public.inventory i join public.products p on p.id=i.product_id and p.company_id=i.company_id where i.company_id=c and i.location_id=loc.id and i.quantity>0 and p.active order by md5(i.product_id::text) loop
 remaining:=trunc(prod.quantity);
 while remaining>0 and slot<=slot_count loop
 take:=least(counts[slot],remaining);rr:=((slot-1)/(bays*5))+1;bb:=((slot-1)/5)%bays+1;ll:=(slot-1)%5+1;
 rackid:='R'||rr||'-B'||bb;
 if take>0 then insert into dpq.rack_stock values(c,loc.id,rackid,ll,prod.product_id,take,2,false);end if;
 counts[slot]:=counts[slot]-take;remaining:=remaining-take;if counts[slot]=0 then slot:=slot+1;end if;
 end loop;
 end loop;n:=n+1;
 end loop;return n;
end $$;

create or replace function public.dpq_retail(p_action text,p_payload jsonb default '{}',p_device text default '')
returns jsonb language plpgsql security definer set search_path='' as $$
declare s jsonb;c uuid;u uuid:=auth.uid();r text;req uuid;prior dpq.operations%rowtype;result jsonb;body jsonb;item jsonb;
 idv uuid;lid uuid;pid uuid;channel uuid;customer uuid;namev text;kindv text;v integer;activev boolean;
 old_offer dpq.retail_offers%rowtype;old_customer dpq.retail_customers%rowtype;discount numeric;price numeric;cost numeric;
 starts timestamptz;ends timestamptz;items jsonb;quote jsonb;total numeric:=0;paid numeric:=0;qty numeric;saleid uuid;
 receipt dpq.sale_receipts%rowtype;original dpq.sales_ledger%rowtype;link dpq.retail_sale_links%rowtype;oldqty numeric;
 caps jsonb;queryv text;d record;
begin
 if u is null then raise exception 'DPQ_AUTH: Oturum açın';end if;
 s:=public.dpq_call('status','{}',p_device);c:=(s->>'company_id')::uuid;r:=s->>'role';
 if not coalesce((s->>'allowed')::boolean,false) or not coalesce((s->>'enabled')::boolean,false) then raise exception 'DPQ_LICENSE: Etkin abonelik gerekli';end if;
 if not exists(select 1 from dpq.devices where company_id=c and code=p_device and user_id=u and active) then raise exception 'DPQ_DEVICE: Bu kullanıcı için etkin cihaz gerekli';end if;
 if jsonb_typeof(p_payload) is distinct from 'object' or octet_length(p_payload::text)>300000 then raise exception 'DPQ_INPUT: Geçersiz veya çok büyük istek';end if;
 perform 1 from dpq.settings where company_id=c for update;
 select jsonb_object_agg(cap,dpq.retail_can(c,u,p_device,r,cap)) into caps from unnest(array['offers','layout','finance','customers']) cap;
 if p_action='retail_snapshot' then
 result:=public.dpq_call('snapshot','{}',p_device)-'sales'-'orders';
 return result||jsonb_build_object('capabilities',caps,'role',r,
 'offers',coalesce((select jsonb_agg(to_jsonb(o)) from dpq.retail_offers o where company_id=c),'[]'),
 'layouts',coalesce((select jsonb_agg(to_jsonb(l)) from dpq.rack_layouts l where company_id=c),'[]'),
 'shelves',coalesce((select jsonb_agg(to_jsonb(x)) from dpq.rack_stock x where company_id=c),'[]'),
 'finance_today',case when (caps->>'finance')::boolean then dpq.retail_finance(c,jsonb_build_object('from',(clock_timestamp() at time zone 'Europe/Istanbul')::date,'to',(clock_timestamp() at time zone 'Europe/Istanbul')::date)) else '{}'::jsonb end,
 'server_time',clock_timestamp());
 elsif p_action='retail_quote' then
 if r not in ('owner','admin','branch','employee','manager') then raise exception 'DPQ_ROLE: Satış yetkisi gerekli';end if;
 return dpq.retail_quote(c,u,p_device,r,p_payload);
 elsif p_action='retail_finance' then
 if not (caps->>'finance')::boolean then raise exception 'DPQ_ROLE: Mali tablo yetkisi gerekli';end if;
 return dpq.retail_finance(c,p_payload);
 elsif p_action='retail_customers' then
 if r not in ('owner','admin','branch','employee','manager') and not (caps->>'customers')::boolean then raise exception 'DPQ_ROLE: Müşteri erişim yetkisi gerekli';end if;
 queryv:=left(trim(coalesce(p_payload->>'query','')),200);
 return coalesce((select jsonb_agg(to_jsonb(x)) from (select * from dpq.retail_customers where company_id=c
 and (lower(name) like '%'||lower(queryv)||'%' or phone like '%'||queryv||'%' or lower(email) like '%'||lower(queryv)||'%')
 order by active desc,name,id limit 100 offset least(100000,greatest(0,coalesce((p_payload->>'offset')::integer,0)))) x),'[]');
 elsif p_action='retail_receipt' then
 select * into receipt from dpq.sale_receipts where company_id=c and id=(p_payload->>'id')::uuid;
 if not found or (receipt.actor<>u and not (caps->>'finance')::boolean) then raise exception 'DPQ_ROLE: Fiş bulunamadı veya yetkiniz yok';end if;
 return to_jsonb(receipt)||jsonb_build_object('returns',coalesce((select jsonb_agg(to_jsonb(e)) from dpq.sales_ledger e join dpq.retail_sale_links k on k.sale_id=e.id and k.company_id=c where k.receipt_id=receipt.id and e.kind='return'),'[]'));
 elsif p_action='retail_grants' then
 if r<>'owner' then raise exception 'DPQ_OWNER: Ana yönetici gerekli';end if;
 return jsonb_build_object('grants',coalesce((select jsonb_agg(to_jsonb(g)) from dpq.retail_grants g where company_id=c),'[]'),
 'devices',coalesce((select jsonb_agg(to_jsonb(x)) from dpq.devices x where company_id=c and active),'[]'));
 end if;
 if r not in ('owner','admin','branch','employee','manager','warehouse') then raise exception 'DPQ_ROLE: Salt okunur hesap';end if;
 req:=(p_payload->>'request_id')::uuid;
 if req is null then raise exception 'DPQ_REQUEST: İşlem kimliği gerekli';end if;
 select * into prior from dpq.operations where company_id=c and request_id=req;
 if found then
 if prior.action<>p_action or prior.payload<>p_payload or prior.actor<>u then raise exception 'DPQ_REPLAY: İşlem kimliği farklı içerikle kullanıldı';end if;
 return prior.result;
 end if;
 if p_action='retail_offer_save' then
 if not (caps->>'offers')::boolean then raise exception 'DPQ_ROLE: Kampanya ve set düzenleme yetkisi gerekli';end if;
 idv:=coalesce(nullif(p_payload->>'id','')::uuid,req);body:=p_payload->'data';kindv:=body->>'kind';namev:=trim(body->>'name');discount:=(body->>'discount')::numeric;
 starts:=(body->>'starts_at')::timestamptz;ends:=(body->>'ends_at')::timestamptz;items:=body->'items';
 if namev is null or length(namev) not between 1 and 150 or kindv is null or kindv not in ('campaign','bundle')
 or discount is null or discount not between .01 and 99.99 or discount<>round(discount,2) or starts is null or ends is null or ends<=starts
 or jsonb_typeof(items) is distinct from 'array' or jsonb_array_length(items) not between 1 and 200 then raise exception 'DPQ_INPUT: Kampanya adı, tarihleri, oranı ve ürünleri kontrol edin';end if;
 select * into old_offer from dpq.retail_offers where company_id=c and id=idv;
 if old_offer.id is not null and (old_offer.version<>coalesce((p_payload->>'version')::integer,0) or old_offer.kind<>kindv) then raise exception 'DPQ_CONFLICT: Kampanya veya set değişti; yenileyin';end if;
 if exists(select 1 from jsonb_array_elements(items) x group by x->>'product_id' having count(*)>1) then raise exception 'DPQ_INPUT: Aynı ürün tek satırda olmalı';end if;
 for item in select value from jsonb_array_elements(items) loop
 pid:=(item->>'product_id')::uuid;qty:=(item->>'quantity')::numeric;
 if qty is null or qty not between 1 and 1000000 or qty<>trunc(qty) then raise exception 'DPQ_INPUT: Tam sayı adet gerekli';end if;
 select sale_price,purchase_price into price,cost from public.products where company_id=c and id=pid and active;
 if not found then raise exception 'DPQ_PRODUCT: Etkin ürün bulunamadı';end if;
 if round(price*(1-discount/100),2)<cost then raise exception 'DPQ_COST: İndirimli fiyat maliyetin altına düşüyor';end if;
 end loop;
 if jsonb_typeof(body->'location_ids') is distinct from 'array' then raise exception 'DPQ_INPUT: Konum listesi gerekli';end if;
 for item in select value from jsonb_array_elements(body->'location_ids') loop
 if not exists(select 1 from public.locations where company_id=c and id=(item#>>'{}')::uuid and active) then raise exception 'DPQ_LOCATION: Geçersiz konum';end if;
 end loop;
 insert into dpq.retail_offers(company_id,id,kind,name,items,discount,starts_at,ends_at,member_only,location_ids,active,actor)
 values(c,idv,kindv,namev,items,discount,starts,ends,coalesce((body->>'member_only')::boolean,false),body->'location_ids',coalesce((body->>'active')::boolean,true),u)
 on conflict(company_id,id) do update set name=excluded.name,items=excluded.items,discount=excluded.discount,starts_at=excluded.starts_at,ends_at=excluded.ends_at,
 member_only=excluded.member_only,location_ids=excluded.location_ids,active=excluded.active,version=dpq.retail_offers.version+1,updated_at=clock_timestamp(),actor=u;
 select to_jsonb(o) into result from dpq.retail_offers o where company_id=c and id=idv;
 elsif p_action='retail_customer_save' then
 if not (caps->>'customers')::boolean then raise exception 'DPQ_ROLE: Müşteri düzenleme yetkisi gerekli';end if;
 idv:=coalesce(nullif(p_payload->>'id','')::uuid,req);body:=p_payload->'data';namev:=trim(body->>'name');
 if namev is null or length(namev) not between 2 and 150 or length(coalesce(body->>'phone',''))>40 or length(coalesce(body->>'email',''))>254 or length(coalesce(body->>'consent_note',''))>1000 then raise exception 'DPQ_INPUT: Müşteri bilgilerini kontrol edin';end if;
 if coalesce(body->>'email','')<>'' and body->>'email' !~ '^[^[:space:]@]+@[^[:space:]@]+\.[^[:space:]@]+$' then raise exception 'DPQ_INPUT: Geçerli e-posta girin';end if;
 if coalesce((body->>'email_consent')::boolean,false) and coalesce(body->>'email','')='' then raise exception 'DPQ_INPUT: E-posta izni için adres gerekli';end if;
 if coalesce((body->>'sms_consent')::boolean,false) and coalesce(body->>'phone','')='' then raise exception 'DPQ_INPUT: SMS izni için telefon gerekli';end if;
 select * into old_customer from dpq.retail_customers where company_id=c and id=idv;
 if old_customer.id is not null and old_customer.version<>coalesce((p_payload->>'version')::integer,0) then raise exception 'DPQ_CONFLICT: Müşteri değişti; yenileyin';end if;
 if (coalesce((body->>'member')::boolean,false) or coalesce((body->>'email_consent')::boolean,false) or coalesce((body->>'sms_consent')::boolean,false))
 and length(trim(coalesce(body->>'consent_note','')))<3 then raise exception 'DPQ_CONSENT: Müşterinin izin verdiği tarih, yöntem ve izin kaynağını belirtin';end if;
 insert into dpq.retail_customers(company_id,id,name,phone,email,member,email_consent,sms_consent,consent_note,consent_at,active,actor)
 values(c,idv,namev,trim(coalesce(body->>'phone','')),lower(trim(coalesce(body->>'email',''))),coalesce((body->>'member')::boolean,false),
 coalesce((body->>'email_consent')::boolean,false),coalesce((body->>'sms_consent')::boolean,false),coalesce(body->>'consent_note',''),clock_timestamp(),coalesce((body->>'active')::boolean,true),u)
 on conflict(company_id,id) do update set name=excluded.name,phone=excluded.phone,email=excluded.email,member=excluded.member,
 email_consent=excluded.email_consent,sms_consent=excluded.sms_consent,consent_note=excluded.consent_note,consent_at=excluded.consent_at,active=excluded.active,
 version=dpq.retail_customers.version+1,actor=u,updated_at=clock_timestamp();
 insert into dpq.retail_consent_history(company_id,customer_id,actor,member,email_consent,sms_consent,evidence)
 select c,idv,u,member,email_consent,sms_consent,consent_note from dpq.retail_customers where company_id=c and id=idv;
 select to_jsonb(x) into result from dpq.retail_customers x where company_id=c and id=idv;
 elsif p_action='retail_layout_save' or p_action='retail_shelf_place' then
 if not (caps->>'layout')::boolean then raise exception 'DPQ_ROLE: Raf düzenleme yetkisi gerekli';end if;
 result:=dpq.retail_layout(c,u,case when p_action='retail_layout_save' then 'save' else 'place' end,p_payload);
 elsif p_action='retail_seed_layouts' then
 if not (caps->>'layout')::boolean then raise exception 'DPQ_ROLE: Raf düzenleme yetkisi gerekli';end if;
 result:=jsonb_build_object('seeded',dpq.retail_seed(c,u));
 elsif p_action='retail_sale' then
 if r not in ('owner','admin','branch','employee','manager') then raise exception 'DPQ_ROLE: Satış yetkisi gerekli';end if;
 quote:=dpq.retail_quote(c,u,p_device,r,p_payload);
 if quote->>'fingerprint' is distinct from p_payload->>'fingerprint' then raise exception 'DPQ_PRICE: Sepet tutarı veya kampanya değişti; tekrar hesaplayın';end if;
 lid:=(quote->>'location_id')::uuid;channel:=(quote->>'channel_id')::uuid;customer:=(quote->>'customer_id')::uuid;items:='[]';
 if jsonb_typeof(p_payload->'payments') is distinct from 'array' or jsonb_array_length(p_payload->'payments') not between 1 and 2 then raise exception 'DPQ_PAYMENT: Ödeme bilgisi gerekli';end if;
 if exists(select 1 from jsonb_array_elements(p_payload->'payments') x group by x->>'type' having count(*)>1) then raise exception 'DPQ_PAYMENT: Aynı ödeme türü yinelenemez';end if;
 for item in select value from jsonb_array_elements(p_payload->'payments') loop
 price:=(item->>'amount')::numeric;
 if coalesce(item->>'type','') not in ('cash','card') or price is null or price not between 0 and 1000000000 or price<>round(price,2) then raise exception 'DPQ_PAYMENT: Geçersiz ödeme';end if;
 paid:=paid+price;
 end loop;
 if paid<>(quote->>'total')::numeric then raise exception 'DPQ_PAYMENT: Nakit ve kart toplamı sepet tutarıyla eşleşmeli';end if;
 for item in select value from jsonb_array_elements(quote->'lines') loop
 saleid:=gen_random_uuid();pid:=(item->>'product_id')::uuid;qty:=(item->>'quantity')::numeric;price:=(item->>'price')::numeric;
 perform public.dpq_call('sale',jsonb_build_object('request_id',saleid,'product_id',pid,'location_id',lid,'quantity',qty),p_device);
 update dpq.sales_ledger set unit_price=price where company_id=c and id=saleid;
 insert into dpq.retail_sale_links(company_id,sale_id,receipt_id,channel_id,customer_id,offer_id) values(c,saleid,req,channel,customer,(item->>'offer_id')::uuid);
 items:=items||jsonb_build_array((item-'cost')||jsonb_build_object('sale_id',saleid));
 end loop;
 insert into dpq.sale_receipts(id,company_id,actor,location_id,items,payments,total) values(req,c,u,lid,items,p_payload->'payments',paid);
 result:=jsonb_build_object('id',req,'total',paid,'items',items);
 elsif p_action='retail_return' then
 if not (caps->>'finance')::boolean then raise exception 'DPQ_ROLE: İade için mali işlem yetkisi gerekli';end if;
 saleid:=(p_payload->>'sale_id')::uuid;qty:=(p_payload->>'quantity')::numeric;
 if qty is null or qty<>trunc(qty) or qty not between 1 and 1000000 or coalesce((p_payload->>'inspected')::boolean,false)=false then raise exception 'DPQ_RETURN: İade adedini girip ürünün teslim alındığını doğrulayın';end if;
 select * into original from dpq.sales_ledger where company_id=c and id=saleid and kind='sale';
 select * into link from dpq.retail_sale_links where company_id=c and sale_id=saleid and original_sale_id is null;
 if original.id is null or link.sale_id is null then raise exception 'DPQ_RETURN: Bu kasa satışının fişi bulunamadı';end if;
 select coalesce(sum(e.quantity),0) into oldqty from dpq.retail_sale_links k join dpq.sales_ledger e on e.id=k.sale_id where k.company_id=c and k.original_sale_id=saleid;
 if qty+oldqty>original.quantity then raise exception 'DPQ_RETURN: Satılandan veya kalan iade hakkından fazla iade yapılamaz';end if;
 perform set_config('dpq.internal',c::text,true);
 insert into public.inventory(company_id,product_id,location_id,quantity) values(c,original.product_id,original.location_id,qty)
 on conflict(company_id,location_id,product_id) do update set quantity=public.inventory.quantity+excluded.quantity,updated_at=clock_timestamp();
 insert into dpq.sales_ledger(id,company_id,product_id,location_id,quantity,kind,unit_price,unit_cost) values(req,c,original.product_id,original.location_id,qty,'return',original.unit_price,original.unit_cost);
 insert into dpq.retail_sale_links(company_id,sale_id,receipt_id,channel_id,customer_id,original_sale_id,offer_id) values(c,req,link.receipt_id,link.channel_id,link.customer_id,saleid,link.offer_id);
 result:=jsonb_build_object('id',req,'refund',qty*original.unit_price);
 elsif p_action='retail_expense' then
 if not (caps->>'finance')::boolean then raise exception 'DPQ_ROLE: Mali işlem yetkisi gerekli';end if;
 lid:=nullif(p_payload->>'location_id','')::uuid;channel:=nullif(p_payload->>'channel_id','')::uuid;price:=(p_payload->>'amount')::numeric;namev:=trim(p_payload->>'name');
 if price is null or price not between .01 and 100000000 or price<>round(price,2) or length(coalesce(namev,'')) not between 2 and 200 or (p_payload->>'incurred_on')::date is null then raise exception 'DPQ_INPUT: Gider adı, tarihi ve tutarı gerekli';end if;
 if lid is not null and not exists(select 1 from public.locations where company_id=c and id=lid) then raise exception 'DPQ_LOCATION: Geçersiz konum';end if;
 if channel is not null and not exists(select 1 from dpq.channels where company_id=c and id=channel) then raise exception 'DPQ_CHANNEL: Geçersiz kanal';end if;
 insert into dpq.retail_expenses(company_id,id,location_id,channel_id,name,amount,incurred_on,actor) values(c,req,lid,channel,namev,price,(p_payload->>'incurred_on')::date,u);
 result:=jsonb_build_object('id',req);
 elsif p_action='retail_expense_void' then
 if not (caps->>'finance')::boolean then raise exception 'DPQ_ROLE: Mali işlem yetkisi gerekli';end if;
 update dpq.retail_expenses set active=false where company_id=c and id=(p_payload->>'id')::uuid and active;
 if not found then raise exception 'DPQ_CONFLICT: Gider kaydı değişti';end if;result:='{"void":true}';
 elsif p_action='retail_location_save' then
 if r<>'owner' then raise exception 'DPQ_OWNER: Şube/depo düzenlemek için ana yönetici gerekli';end if;
 idv:=coalesce(nullif(p_payload->>'id','')::uuid,req);namev:=trim(p_payload->>'name');kindv:=p_payload->>'location_type';activev:=coalesce((p_payload->>'active')::boolean,true);
 if length(coalesce(namev,'')) not between 1 and 100 or kindv is null or kindv not in ('center','warehouse','branch') then raise exception 'DPQ_INPUT: Konum adı ve türü gerekli';end if;
 if exists(select 1 from public.locations where id=idv and company_id<>c) then raise exception 'DPQ_ROLE: Başka işletmeye ait konum';end if;
 if exists(select 1 from public.locations where id=idv and company_id=c) and
 not exists(select 1 from public.locations where id=idv and company_id=c and name=p_payload->'expected'->>'name' and active=(p_payload->'expected'->>'active')::boolean and location_type=p_payload->'expected'->>'location_type') then raise exception 'DPQ_CONFLICT: Konum değişti; yenileyin';end if;
 if not activev and (exists(select 1 from public.inventory where company_id=c and location_id=idv and quantity<>0)
 or exists(select 1 from dpq.allocations a join dpq.orders o on o.id=a.order_id where o.company_id=c and (a.location_id=idv or a.target_id=idv) and a.state in ('reserved','transit'))
 or exists(select 1 from dpq.counter_orders where company_id=c and (origin_id=idv or location_id=idv) and status='reserved')
 or exists(select 1 from dpq.settings where company_id=c and center_id=idv)) then raise exception 'DPQ_LOCATION_STOCK: Konumda stok/açık işlem var veya merkez olarak kullanılıyor';end if;
 perform set_config('dpq.internal',c::text,true);
 insert into public.locations(id,company_id,name,location_type,active) values(idv,c,namev,kindv,activev)
 on conflict(id) do update set name=excluded.name,location_type=excluded.location_type,active=excluded.active;
 result:=jsonb_build_object('id',idv);
 elsif p_action='retail_channel_save' then
 if r<>'owner' then raise exception 'DPQ_OWNER: Kanal düzenlemek için ana yönetici gerekli';end if;
 idv:=coalesce(nullif(p_payload->>'id','')::uuid,req);namev:=trim(p_payload->>'name');activev:=coalesce((p_payload->>'active')::boolean,true);
 if length(coalesce(namev,'')) not between 1 and 100 then raise exception 'DPQ_INPUT: Kanal adı gerekli';end if;
 if exists(select 1 from dpq.channels where id=idv and company_id<>c) then raise exception 'DPQ_ROLE: Başka işletmeye ait kanal';end if;
 if exists(select 1 from dpq.channels where id=idv and company_id=c) and
 not exists(select 1 from dpq.channels where id=idv and company_id=c and name=p_payload->'expected'->>'name' and active=(p_payload->'expected'->>'active')::boolean) then raise exception 'DPQ_CONFLICT: Kanal değişti; yenileyin';end if;
 insert into dpq.channels(id,company_id,name,active) values(idv,c,namev,activev)
 on conflict(id) do update set name=excluded.name,active=excluded.active;
 result:=jsonb_build_object('id',idv);
 elsif p_action='retail_grant_save' then
 if r<>'owner' then raise exception 'DPQ_OWNER: Yetkilendirme için ana yönetici gerekli';end if;
 idv:=(p_payload->>'user_id')::uuid;namev:=p_payload->>'device';kindv:=p_payload->>'capability';
 if kindv is null or kindv not in ('offers','layout','finance','customers') or not exists(select 1 from dpq.devices where company_id=c and user_id=idv and code=namev and active)
 or not exists(select 1 from public.company_members where company_id=c and user_id=idv and active and role<>'viewer') then raise exception 'DPQ_DEVICE: Etkin kullanıcı ve cihaz seçin';end if;
 delete from dpq.retail_grants where company_id=c and user_id=idv and device=namev and capability=kindv;
 if coalesce((p_payload->>'enabled')::boolean,false) then insert into dpq.retail_grants values(c,idv,namev,kindv);end if;
 result:=jsonb_build_object('saved',true);
 else raise exception 'DPQ_ACTION: Bilinmeyen perakende işlemi';end if;
 insert into dpq.operations(company_id,request_id,actor,action,payload,result) values(c,req,u,p_action,p_payload,result);
 -- Consent evidence belongs only in the protected customer history, not general audit exports.
 insert into dpq.audit(company_id,actor,action,payload) values(c,u,p_action,jsonb_build_object('request_id',req,'record_id',coalesce(idv,req)));
 return result;
end $$;
revoke all on function public.dpq_retail(text,jsonb,text) from public,anon;
grant execute on function public.dpq_retail(text,jsonb,text) to authenticated;
revoke all on function dpq.retail_can(uuid,uuid,text,text,text),dpq.retail_quote(uuid,uuid,text,text,jsonb),dpq.retail_finance(uuid,jsonb),dpq.retail_layout(uuid,uuid,text,jsonb),dpq.retail_seed(uuid,uuid),dpq.rack_reconcile() from public,anon,authenticated;
create or replace function public.dpq_0280_ready() returns text language sql security invoker set search_path='' as $$ select '0.28.0'::text $$;
revoke all on function public.dpq_0280_ready() from public,anon;
grant execute on function public.dpq_0280_ready() to authenticated;
commit;
