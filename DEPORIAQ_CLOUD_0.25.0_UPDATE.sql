-- DeporiaQ 0.25.0 update for an existing 0.24.1+ database.
-- Atomic additive migration; does not change subscription dates or current stock.
begin;
do $$ begin
 if to_regprocedure('public.dpq_call(text,jsonb,text)') is null then raise exception 'Önce 0.24 sunucu kurulumu gerekli';end if;
end $$;
-- Live sessions are separate from licensed device registrations.
create table if not exists dpq.user_directory (
 company_id uuid not null references public.companies(id),user_id uuid not null,display_name text not null,
 primary key(company_id,user_id)
);
alter table dpq.user_directory enable row level security;
revoke all on dpq.user_directory from public,anon,authenticated;
create table if not exists dpq.presence (
 company_id uuid not null references public.companies(id),
 user_id uuid not null, device text not null, session_id uuid not null,
 display_name text not null, seen_at timestamptz not null default clock_timestamp(),
 primary key(company_id,user_id,device,session_id)
);
alter table dpq.presence enable row level security;
revoke all on dpq.presence from public,anon,authenticated;
create or replace function public.dpq_presence(p_device text,p_session uuid,p_name text default '',p_leave boolean default false)
returns jsonb language plpgsql security definer set search_path='' as $$
declare c uuid;u uuid:=auth.uid();
begin
 if u is null or (select count(*) from public.company_members where user_id=u and active)<>1 then raise exception 'DPQ_AUTH: Etkin üyelik gerekli'; end if;
 select company_id into c from public.company_members where user_id=u and active;
 if p_session is null then raise exception 'DPQ_SESSION: Oturum kimliği gerekli'; end if;
 if p_leave then
  delete from dpq.presence where company_id=c and user_id=u and device=p_device and session_id=p_session;
 else
  if not exists(select 1 from public.company_subscriptions where company_id=c and status in ('active','trial','past_due') and valid_until>clock_timestamp()) then raise exception 'DPQ_LICENSE: Abonelik aktif değil'; end if;
  if not exists(select 1 from dpq.devices where company_id=c and code=p_device and active) then raise exception 'DPQ_DEVICE: Etkin cihaz gerekli'; end if;
  if length(trim(p_name)) not between 1 and 100 then raise exception 'DPQ_INPUT: Kullanıcı adı gerekli'; end if;
  insert into dpq.user_directory values(c,u,trim(p_name)) on conflict(company_id,user_id) do update set display_name=excluded.display_name;
  insert into dpq.presence values(c,u,p_device,p_session,trim(p_name),clock_timestamp())
  on conflict(company_id,user_id,device,session_id) do update set seen_at=excluded.seen_at,display_name=excluded.display_name;
 end if;
 delete from dpq.presence where company_id=c and seen_at<clock_timestamp()-interval '30 seconds';
 return coalesce((select jsonb_agg(jsonb_build_object('user_id',x.user_id,'name',x.display_name)) from
 (select distinct on (p.user_id) p.user_id,p.display_name from dpq.presence p
 join public.company_members m on m.company_id=p.company_id and m.user_id=p.user_id and m.active
 join dpq.devices d on d.company_id=p.company_id and d.code=p.device and d.active
 where p.company_id=c and p.seen_at>clock_timestamp()-interval '30 seconds'
 order by p.user_id,p.seen_at desc) x),'[]');
end $$;
revoke all on function public.dpq_presence(text,uuid,text,boolean) from public,anon;
grant execute on function public.dpq_presence(text,uuid,text,boolean) to authenticated;

-- 0.25 workspace foundation. No subscription dates are written.
create table if not exists dpq.workspace_records (
 company_id uuid not null references public.companies(id),id uuid not null default gen_random_uuid(),
 kind text not null check(kind in ('product','supplier','purchase','damage','batch','task','basket','bundle','receipt','approval')),
 data jsonb not null,actor uuid not null,version integer not null default 1,
 updated_at timestamptz not null default now(),primary key(company_id,id)
);
alter table dpq.workspace_records enable row level security;
revoke all on dpq.workspace_records from public,anon,authenticated;
create table if not exists dpq.sale_receipts (
 id uuid primary key,company_id uuid not null,actor uuid not null,location_id uuid not null,
 items jsonb not null,payments jsonb not null,total numeric(16,2) not null,created_at timestamptz not null default now()
);
alter table dpq.sale_receipts enable row level security;
revoke all on dpq.sale_receipts from public,anon,authenticated;
alter table dpq.settings add column if not exists staff_discount_limit numeric not null default 0 check(staff_discount_limit between 0 and 100);
create or replace function public.dpq_workspace(p_action text,p_payload jsonb default '{}',p_device text default '')
returns jsonb language plpgsql security definer set search_path='' as $$
declare c uuid;u uuid:=auth.uid();s jsonb;admin boolean;role_name text;req uuid;prior dpq.operations%rowtype;
 result jsonb;row_data dpq.workspace_records%rowtype;k text;rid uuid;body jsonb;item jsonb;line jsonb;pid uuid;lid uuid;
 qty numeric;price numeric;cost numeric;discount numeric;max_discount numeric;total numeric:=0;paid numeric:=0;items jsonb:='[]';saleid uuid;
 loc_ok boolean;reference_price numeric;approval_id uuid;
begin
 s:=public.dpq_call('status','{}',p_device);c:=(s->>'company_id')::uuid;role_name:=s->>'role';admin:=role_name in ('owner','admin');
 if not (s->>'allowed')::boolean or not (s->>'enabled')::boolean then raise exception 'DPQ_LICENSE: Etkin abonelik gerekli';end if;
 if not exists(select 1 from dpq.devices where company_id=c and code=p_device and active) then raise exception 'DPQ_DEVICE: Etkin cihaz gerekli';end if;
 perform 1 from dpq.settings where company_id=c for update;
 if p_action='workspace_list' then
 return jsonb_build_object('records',coalesce((select jsonb_agg(to_jsonb(w)||jsonb_build_object('data',w.data-'image_jpeg','has_image',w.data ? 'image_jpeg')) from dpq.workspace_records w where company_id=c
 and (admin or kind in ('product','bundle','batch') or (kind in ('basket','approval') and actor=u) or (kind='task' and (actor=u or data->>'assignee'=u::text)))),'[]'),
 'members',coalesce((select jsonb_agg(jsonb_build_object('id',m.user_id,'name',coalesce(d.display_name,m.user_id::text))) from public.company_members m left join dpq.user_directory d on d.company_id=m.company_id and d.user_id=m.user_id where m.company_id=c and m.active),'[]'),
 'discount_limit',(select staff_discount_limit from dpq.settings where company_id=c));
 end if;
 if p_action='workspace_record' then
 select * into row_data from dpq.workspace_records where company_id=c and id=(p_payload->>'id')::uuid;
 if not found or not (admin or row_data.kind in ('product','bundle','batch') or row_data.actor=u or (row_data.kind='task' and row_data.data->>'assignee'=u::text)) then raise exception 'DPQ_ROLE: Kayıt bulunamadı veya yetkiniz yok';end if;
 return to_jsonb(row_data);
 end if;
 if p_action='workspace_support_status' then
 return coalesce((select jsonb_agg(jsonb_build_object('id',id,'subject',subject,'mail_status',mail_status,'created_at',created_at,'attempts',attempts)) from dpq.tickets where company_id=c and actor=u),'[]');
 end if;
 if role_name not in ('owner','admin','manager','employee','branch','warehouse') then raise exception 'DPQ_ROLE: Salt okunur hesap';end if;
 req:=(p_payload->>'request_id')::uuid;if req is null then raise exception 'DPQ_REQUEST: İşlem kimliği gerekli';end if;
 select * into prior from dpq.operations where company_id=c and request_id=req;
 if found then
 if prior.actor<>u or prior.action<>p_action or prior.payload<>p_payload then raise exception 'DPQ_REPLAY: Farklı işlem içeriği';end if;
 return prior.result;
 end if;
 if p_action='workspace_save' then
 k:=p_payload->>'kind';rid:=coalesce(nullif(p_payload->>'id','')::uuid,req);body:=p_payload->'data';
 if k is null or k not in ('product','supplier','purchase','batch','task','basket','bundle') or jsonb_typeof(body) is distinct from 'object' or length(body::text)>2000000 then raise exception 'DPQ_INPUT: Geçersiz kayıt';end if;
 if not admin and k not in ('basket','task') then raise exception 'DPQ_ROLE: Yönetici gerekli';end if;
 select * into row_data from dpq.workspace_records where company_id=c and id=rid for update;
 if found then
 if row_data.kind<>k or (not admin and row_data.actor<>u and not (k='task' and row_data.data->>'assignee'=u::text)) then raise exception 'DPQ_ROLE: Kayıt yetkisi yok';end if;
 if row_data.version<>coalesce((p_payload->>'version')::integer,0) then raise exception 'DPQ_CONFLICT: Kayıt değişti; yenileyin';end if;
 end if;
 if k in ('product','batch') then
 pid:=(body->>'product_id')::uuid;
 if not exists(select 1 from public.products where company_id=c and id=pid) then raise exception 'DPQ_PRODUCT: Ürün bulunamadı';end if;
 if k='product' and body ? 'image_jpeg' and octet_length(decode(body->>'image_jpeg','base64'))>350000 then raise exception 'DPQ_INPUT: Görsel çok büyük';end if;
 if k='batch' then
 if length(trim(coalesce(body->>'lot','')))=0 or (body->>'expires')::date is null then raise exception 'DPQ_INPUT: Parti numarası ve son kullanma tarihi gerekli';end if;
 end if;
 if k='product' and exists(select 1 from dpq.workspace_records where company_id=c and kind='product' and data->>'product_id'=pid::text and id<>rid) then raise exception 'DPQ_CONFLICT: Ürünün ayrıntı kartı var; mevcut kartı açın';end if;
 elsif k in ('supplier','task','basket','bundle','purchase') then
 if length(trim(coalesce(body->>'name',''))) not between 1 and 200 then raise exception 'DPQ_INPUT: Ad gerekli';end if;
 end if;
 if k='task' then
 if not exists(select 1 from public.company_members where company_id=c and user_id=(body->>'assignee')::uuid and active) then raise exception 'DPQ_INPUT: Etkin sorumlu seçin';end if;
 if coalesce(body->>'status','') not in ('Yapılacak','Devam ediyor','Tamamlandı') then raise exception 'DPQ_INPUT: Görev durumu geçersiz';end if;
 if coalesce(body->>'due','')<>'' then perform (body->>'due')::date;end if;
 end if;
 if k='purchase' and exists(select 1 from dpq.workspace_records where company_id=c and kind='receipt' and data->>'purchase_id'=rid::text) and body->'items' is distinct from row_data.data->'items' then raise exception 'DPQ_STATE: Teslim alınmış siparişin ürün satırları değiştirilemez';end if;
 if k='purchase' and not exists(select 1 from dpq.workspace_records where company_id=c and id=(body->>'supplier_id')::uuid and kind='supplier') then raise exception 'DPQ_INPUT: Tedarikçi seçin';end if;
 if k in ('basket','bundle','purchase') then
 if jsonb_typeof(body->'items') is distinct from 'array' or jsonb_array_length(body->'items') not between 1 and 200 then raise exception 'DPQ_INPUT: Ürün satırları gerekli';end if;
 for item in select value from jsonb_array_elements(body->'items') loop
 pid:=(item->>'product_id')::uuid;qty:=(item->>'quantity')::numeric;
 if qty is null or qty<>trunc(qty) or qty not between 1 and 1000000 then raise exception 'DPQ_INPUT: Tam sayı adet gerekli';end if;
 if not exists(select 1 from public.products where company_id=c and id=pid and active) then raise exception 'DPQ_PRODUCT: Ürün bulunamadı';end if;
 end loop;
 end if;
 insert into dpq.workspace_records(company_id,id,kind,data,actor) values(c,rid,k,body,u)
 on conflict(company_id,id) do update set data=excluded.data,version=dpq.workspace_records.version+1,updated_at=clock_timestamp();
 select to_jsonb(w) into result from dpq.workspace_records w where company_id=c and id=rid;
 elsif p_action='workspace_discount_policy' then
 if not admin then raise exception 'DPQ_ROLE: Yönetici gerekli';end if;
 max_discount:=(p_payload->>'limit')::numeric;
 if max_discount is null or max_discount not between 0 and 100 then raise exception 'DPQ_INPUT: 0–100 arası oran gerekli';end if;
 update dpq.settings set staff_discount_limit=max_discount where company_id=c;result:=jsonb_build_object('limit',max_discount);
 elsif p_action='workspace_cart_sale' then
 if role_name not in ('owner','admin','branch','employee','manager') then raise exception 'DPQ_ROLE: Satış yetkisi yok';end if;
 rid:=nullif(p_payload->>'basket_id','')::uuid;
 if rid is not null then
 select * into row_data from dpq.workspace_records where company_id=c and id=rid and kind='basket' for update;
 if not found or row_data.actor<>u or coalesce((row_data.data->>'closed')::boolean,false) or row_data.version<>coalesce((p_payload->>'basket_version')::integer,0) then raise exception 'DPQ_CONFLICT: Bekleyen sepet değişti veya zaten satıldı';end if;
 end if;
 lid:=(p_payload->>'location_id')::uuid;
 if not exists(select 1 from public.locations where id=lid and company_id=c and active) then raise exception 'DPQ_LOCATION: Konum bulunamadı';end if;
 if not admin and not exists(select 1 from dpq.staff_locations where company_id=c and user_id=u and location_id=lid) then raise exception 'DPQ_LOCATION_ROLE: Konum yetkisi yok';end if;
 if jsonb_typeof(p_payload->'items') is distinct from 'array' or jsonb_array_length(p_payload->'items') not between 1 and 200 then raise exception 'DPQ_INPUT: Sepet boş';end if;
 select case when admin then 100 else staff_discount_limit end into max_discount from dpq.settings where company_id=c;
 approval_id:=nullif(p_payload->>'approval_id','')::uuid;
 if approval_id is not null then
 if not exists(select 1 from dpq.workspace_records where company_id=c and id=approval_id and actor=u and kind='approval' and data->>'status'='approved' and (data->>'expires')::timestamptz>clock_timestamp() and data->'items'=p_payload->'items' and data->>'location_id'=lid::text) then raise exception 'DPQ_APPROVAL: Onay yok, süresi doldu veya sepet değişti';end if;
 max_discount:=100;
 end if;
 for item in select value from jsonb_array_elements(p_payload->'items') loop
 pid:=(item->>'product_id')::uuid;qty:=(item->>'quantity')::numeric;discount:=coalesce((item->>'discount')::numeric,0);
 if qty is null or qty<>trunc(qty) or qty not between 1 and 1000000 or discount not between 0 and max_discount then raise exception 'DPQ_INPUT: Adet veya indirim yetki sınırı geçersiz';end if;
 select sale_price,purchase_price into price,cost from public.products where id=pid and company_id=c and active;
 if not found then raise exception 'DPQ_PRODUCT: Ürün bulunamadı';end if;
 if item ? 'expected_price' and (item->>'expected_price')::numeric<>price then raise exception 'DPQ_PRICE: Fiyat değişti; sepeti yenileyin';end if;
 price:=round(price*(1-discount/100),2);saleid:=gen_random_uuid();
 -- Existing sale RPC applies the subscription, location and reservation checks.
 perform public.dpq_call('sale',jsonb_build_object('request_id',saleid,'product_id',pid,'location_id',lid,'quantity',qty),p_device);
 update dpq.sales_ledger set unit_price=price where id=saleid and company_id=c;
 total:=total+price*qty;items:=items||jsonb_build_array(jsonb_build_object('product_id',pid,'quantity',qty,'price',price,'discount',discount,'sale_id',saleid));
 end loop;
 if jsonb_typeof(p_payload->'payments') is distinct from 'array' or jsonb_array_length(p_payload->'payments') not between 1 and 2 then raise exception 'DPQ_PAYMENT: Nakit/kart tutarı gerekli';end if;
 for item in select value from jsonb_array_elements(p_payload->'payments') loop
 price:=(item->>'amount')::numeric;
 if coalesce(item->>'type','') not in ('cash','card') or price is null or price<0 or price<>round(price,2) or price='NaN'::numeric then raise exception 'DPQ_PAYMENT: Geçersiz ödeme';end if;
 paid:=paid+price;
 end loop;
 if paid<>total then raise exception 'DPQ_PAYMENT: Ödeme toplamı sepet tutarıyla eşleşmiyor';end if;
 if rid is not null then update dpq.workspace_records set data=data||'{"closed":true}',version=version+1 where company_id=c and id=rid;end if;
 if approval_id is not null then update dpq.workspace_records set data=data||'{"status":"used"}',version=version+1 where company_id=c and id=approval_id;end if;
 insert into dpq.sale_receipts values(req,c,u,lid,items,p_payload->'payments',total,clock_timestamp());
 result:=jsonb_build_object('id',req,'total',total,'items',items);
 elsif p_action='workspace_prices' then
 if not admin then raise exception 'DPQ_ROLE: Yönetici gerekli';end if;
 if jsonb_typeof(p_payload->'items') is distinct from 'array' or jsonb_array_length(p_payload->'items') not between 1 and 1000 then raise exception 'DPQ_INPUT: Fiyat satırları gerekli';end if;
 perform set_config('dpq.internal',c::text,true);
 for item in select value from jsonb_array_elements(p_payload->'items') loop
 pid:=(item->>'product_id')::uuid;price:=(item->>'price')::numeric;reference_price:=(item->>'expected_price')::numeric;
 if price is null or price not between 0 and 100000000 or price<>round(price,2) then raise exception 'DPQ_INPUT: Geçersiz fiyat';end if;
 if not exists(select 1 from public.products where company_id=c and id=pid and sale_price=reference_price) then raise exception 'DPQ_CONFLICT: Ürün fiyatı değişti; önizlemeyi yenileyin';end if;
 update public.products set sale_price=price where company_id=c and id=pid;
 end loop;result:=jsonb_build_object('updated',jsonb_array_length(p_payload->'items'));
 elsif p_action='workspace_damage' then
 if not admin then raise exception 'DPQ_ROLE: Yönetici gerekli';end if;
 pid:=(p_payload->>'product_id')::uuid;lid:=(p_payload->>'location_id')::uuid;qty:=(p_payload->>'quantity')::numeric;
 if qty is null or qty<>trunc(qty) or qty not between 1 and 1000000 or length(trim(coalesce(p_payload->>'reason','')))<3 then raise exception 'DPQ_INPUT: Adet ve hasar nedeni gerekli';end if;
 if dpq.available(c,pid,lid)<qty then raise exception 'DPQ_STOCK: Ayrılabilir stok yetersiz';end if;
 perform set_config('dpq.internal',c::text,true);
 update public.inventory set quantity=quantity-qty,updated_at=clock_timestamp() where company_id=c and product_id=pid and location_id=lid;
 if not found then raise exception 'DPQ_PRODUCT: Stok bulunamadı';end if;
 insert into dpq.workspace_records(company_id,id,kind,data,actor) values(c,req,'damage',p_payload-'request_id',u);
 result:=jsonb_build_object('id',req,'quantity',qty);
 elsif p_action='workspace_purchase_receive' then
 if not admin then raise exception 'DPQ_ROLE: Yönetici gerekli';end if;
 rid:=(p_payload->>'purchase_id')::uuid;lid:=(p_payload->>'location_id')::uuid;
 if not exists(select 1 from public.locations where company_id=c and id=lid and active) then raise exception 'DPQ_LOCATION: Etkin konum gerekli';end if;
 select * into row_data from dpq.workspace_records where company_id=c and id=rid and kind='purchase' for update;
 if not found or row_data.version<>coalesce((p_payload->>'version')::integer,0) then raise exception 'DPQ_CONFLICT: Satın alma kaydını yenileyin';end if;
 if jsonb_typeof(p_payload->'items') is distinct from 'array' or jsonb_array_length(p_payload->'items') not between 1 and 200 then raise exception 'DPQ_INPUT: Teslim satırları gerekli';end if;
 body:=row_data.data;
 for item in select value from jsonb_array_elements(p_payload->'items') loop
 pid:=(item->>'product_id')::uuid;qty:=(item->>'accepted')::numeric;cost:=coalesce((item->>'damaged')::numeric,0);
 if qty is null or qty<>trunc(qty) or qty not between 0 and 1000000 or cost<>trunc(cost) or cost not between 0 and 1000000 or qty+cost=0 then raise exception 'DPQ_INPUT: Geçerli teslim adedi gerekli';end if;
 if not exists(select 1 from jsonb_array_elements(body->'items') x where (x->>'product_id')::uuid=pid) then raise exception 'DPQ_PRODUCT: Siparişte bulunmayan ürün';end if;
 if qty>0 then perform public.dpq_call('receive',jsonb_build_object('request_id',gen_random_uuid(),'product_id',pid,'location_id',lid,'quantity',qty),p_device);end if;
 if cost>0 then insert into dpq.workspace_records(company_id,kind,data,actor) values(c,'damage',jsonb_build_object('product_id',pid,'location_id',lid,'quantity',cost,'reason','Mal kabul hasarı','purchase_id',rid),u);end if;
 end loop;
 insert into dpq.workspace_records(company_id,id,kind,data,actor) values(c,req,'receipt',p_payload-'request_id',u);
 update dpq.workspace_records set version=version+1,updated_at=clock_timestamp() where company_id=c and id=rid;
 result:=jsonb_build_object('id',req,'purchase_id',rid);
 elsif p_action='workspace_import' then
 if not admin then raise exception 'DPQ_ROLE: Yönetici gerekli';end if;
 if jsonb_typeof(p_payload->'items') is distinct from 'array' or jsonb_array_length(p_payload->'items') not between 1 and 500 then raise exception 'DPQ_INPUT: En fazla 500 ürün içe aktarılabilir';end if;
 for item in select value from jsonb_array_elements(p_payload->'items') loop
 if coalesce(item->>'barcode','')<>trim(coalesce(item->>'barcode','')) or length(trim(coalesce(item->>'barcode','')))=0 then raise exception 'DPQ_INPUT: Barkod boş veya kenar boşluk içeriyor';end if;
 if coalesce((item->>'critical_stock')::numeric,0)<0 or coalesce((item->>'critical_stock')::numeric,0)<>trunc(coalesce((item->>'critical_stock')::numeric,0)) then raise exception 'DPQ_INPUT: Kritik stok tam sayı olmalı';end if;
 if exists(select 1 from public.products where company_id=c and barcode=item->>'barcode') then raise exception 'DPQ_CONFLICT: Barkod zaten kayıtlı';end if;
 perform public.dpq_call('catalog_product',item||jsonb_build_object('request_id',gen_random_uuid()),p_device);
 end loop;result:=jsonb_build_object('imported',jsonb_array_length(p_payload->'items'));
 elsif p_action='workspace_discount_request' then
 if jsonb_typeof(p_payload->'items') is distinct from 'array' or jsonb_array_length(p_payload->'items') not between 1 and 200 then raise exception 'DPQ_INPUT: Sepet gerekli';end if;
 lid:=(p_payload->>'location_id')::uuid;
 if not admin and not exists(select 1 from dpq.staff_locations where company_id=c and user_id=u and location_id=lid) then raise exception 'DPQ_LOCATION_ROLE: Konum yetkisi gerekli';end if;
 insert into dpq.workspace_records(company_id,id,kind,data,actor) values(c,req,'approval',jsonb_build_object('items',p_payload->'items','location_id',lid,'status','pending'),u);
 result:=jsonb_build_object('id',req,'status','pending');
 elsif p_action='workspace_discount_approve' then
 if not admin then raise exception 'DPQ_ROLE: Yönetici gerekli';end if;
 update dpq.workspace_records set data=data||jsonb_build_object('status','approved','expires',clock_timestamp()+interval '15 minutes','approved_by',u),version=version+1,updated_at=clock_timestamp()
 where company_id=c and kind='approval' and id=(p_payload->>'id')::uuid and data->>'status'='pending';
 if not found then raise exception 'DPQ_STATE: Bekleyen onay bulunamadı';end if;
 result:=jsonb_build_object('approved',true);
 else raise exception 'DPQ_ACTION: Bilinmeyen işlem';
 end if;
 insert into dpq.operations(company_id,request_id,action,payload,result,actor) values(c,req,p_action,p_payload,result,u);
 return result;
end $$;
revoke all on function public.dpq_workspace(text,jsonb,text) from public,anon;
grant execute on function public.dpq_workspace(text,jsonb,text) to authenticated;

-- User-scoped dispatch leases. SMTP credentials remain in Edge Function secrets.
create or replace function public.dpq_claim_own_support(p_ticket uuid)
returns jsonb language plpgsql security definer set search_path='' as $$
declare ticket dpq.tickets%rowtype;token uuid:=gen_random_uuid();
begin
 if auth.uid() is null then raise exception 'DPQ_AUTH: Oturum gerekli';end if;
 select t.* into ticket from dpq.tickets t join public.company_members m on m.company_id=t.company_id and m.user_id=auth.uid() and m.active
 where t.id=p_ticket and t.actor=auth.uid() and t.mail_status<>'sent' and t.available_at<=clock_timestamp() and t.attempts<10
 for update of t skip locked;
 if not found then return null;end if;
 update dpq.tickets set lease=token,attempts=attempts+1,available_at=clock_timestamp()+interval '5 minutes' where id=ticket.id;
 return to_jsonb(ticket)||jsonb_build_object('lease',token);
end $$;
create or replace function public.dpq_support_status()
returns jsonb language plpgsql security definer set search_path='' as $$
begin
 if auth.uid() is null then raise exception 'DPQ_AUTH: Oturum gerekli';end if;
 return coalesce((select jsonb_agg(jsonb_build_object('id',t.id,'subject',t.subject,'mail_status',t.mail_status,'created_at',t.created_at,'attempts',t.attempts,'available_at',t.available_at) order by t.created_at desc)
 from dpq.tickets t where t.actor=auth.uid() and exists(select 1 from public.company_members m where m.company_id=t.company_id and m.user_id=auth.uid() and m.active)),'[]');
end $$;
revoke all on function public.dpq_claim_own_support(uuid),public.dpq_support_status() from public,anon;
grant execute on function public.dpq_claim_own_support(uuid),public.dpq_support_status() to authenticated;

create or replace function public.dpq_0250_ready() returns text language sql stable set search_path='' as $$ select '0.25.0'::text $$;
revoke all on function public.dpq_0250_ready() from public;
grant execute on function public.dpq_0250_ready() to anon,authenticated,service_role;
commit;
select public.dpq_0250_ready() as installed_version;
