-- 0.27.1: stable product identity, explicit create/edit/archive/delete.
-- No customer rows or subscription dates are changed by this migration.
create or replace function dpq.clean_barcode(value text)
returns text language sql immutable set search_path='' as $$
 select regexp_replace(coalesce(value,''),'^[[:space:]]+|[[:space:]]+$','','g')
$$;
revoke all on function dpq.clean_barcode(text) from public,anon,authenticated;

create or replace function dpq.catalog_change(c uuid,u uuid,op text,body jsonb)
returns jsonb language plpgsql security invoker set search_path='' as $$
declare p public.products%rowtype; pid uuid; code text; title text; price numeric; cost numeric; critical numeric;
 role_name text; expected jsonb; reference_exists boolean; matches integer;
begin
 -- Called only inside dpq_call, after its company lock, license, device and replay checks.
 if u is null or u is distinct from auth.uid() then raise exception 'DPQ_AUTH';end if;
 select role into role_name from public.company_members where company_id=c and user_id=u and active;
 if role_name is null or role_name not in ('owner','admin') then raise exception 'DPQ_ROLE';end if;
 if op is null or op not in ('create','edit','archive','restore','delete','legacy_save') then raise exception 'DPQ_ACTION';end if;
 pid:=nullif(body->>'product_id','')::uuid;
 if op='create' then pid:=null;end if;
 if op='legacy_save' then
  code:=dpq.clean_barcode(body->>'barcode');
  select count(*) into matches from public.products where company_id=c and dpq.clean_barcode(barcode)=code;
  if matches>1 then raise exception 'DPQ_BARCODE_DUPLICATE';end if;
  select id into pid from public.products where company_id=c and dpq.clean_barcode(barcode)=code;
 end if;
 if op<>'create' and (op<>'legacy_save' or pid is not null) then
  select * into p from public.products where company_id=c and id=pid for update;
  if not found then raise exception 'DPQ_PRODUCT';end if;
  expected:=jsonb_build_object('barcode',p.barcode,'name',p.name,'sale_price',p.sale_price,
   'purchase_price',p.purchase_price,'critical_stock',p.critical_stock,'active',p.active);
  if op<>'legacy_save' and body->'expected' is distinct from expected then raise exception 'DPQ_CONFLICT';end if;
 end if;
 if op in ('create','edit','legacy_save') then
  code:=dpq.clean_barcode(body->>'barcode');title:=btrim(body->>'name');
  if length(code) not between 1 and 120 or code ~ '[[:space:][:cntrl:]]' or code ~ '[​‌‍﻿]' then raise exception 'DPQ_BARCODE';end if;
  if title is null or length(title) not between 1 and 250 or title ~ '[[:cntrl:]]' then raise exception 'DPQ_INPUT';end if;
  price:=(body->>'sale_price')::numeric;cost:=(body->>'purchase_price')::numeric;critical:=(body->>'critical_stock')::numeric;
  if price is null or cost is null or critical is null or price not between 0 and 10000000 or cost not between 0 and 10000000
   or price<>round(price,2) or cost<>round(cost,2) or critical not between 0 and 1000000 or critical<>trunc(critical) then raise exception 'DPQ_INPUT';end if;
  if exists(select 1 from public.products where company_id=c and dpq.clean_barcode(barcode)=code and (pid is null or id<>pid)) then raise exception 'DPQ_BARCODE_DUPLICATE';end if;
  if op='create' or (op='legacy_save' and pid is null) then
   insert into public.products(company_id,barcode,name,sale_price,purchase_price,critical_stock,active)
   values(c,code,title,price,cost,critical,true) returning id into pid;
  else
   if op='legacy_save' and not p.active then raise exception 'DPQ_PRODUCT_ARCHIVED';end if;
   update public.products set barcode=code,name=title,sale_price=price,purchase_price=cost,critical_stock=critical where company_id=c and id=pid;
  end if;
 elsif op in ('archive','delete') then
  if exists(select 1 from public.inventory where company_id=c and product_id=pid and quantity<>0) then raise exception 'DPQ_PRODUCT_STOCK';end if;
  if exists(select 1 from dpq.allocations a join dpq.orders o on o.id=a.order_id where o.company_id=c and a.product_id=pid and a.state in ('reserved','transit'))
   or exists(select 1 from dpq.counter_orders where company_id=c and product_id=pid and status in ('reserved','shipped')) then raise exception 'DPQ_RESERVED';end if;
  if op='delete' then
   if role_name<>'owner' then raise exception 'DPQ_OWNER';end if;
   reference_exists:=exists(select 1 from public.stock_movements where company_id=c and product_id=pid)
    or exists(select 1 from public.cloud_operations where company_id=c and product_id=pid)
    or exists(select 1 from dpq.sales_ledger where company_id=c and product_id=pid)
    or exists(select 1 from dpq.allocations a join dpq.orders o on o.id=a.order_id where o.company_id=c and a.product_id=pid)
    or exists(select 1 from dpq.counter_orders where company_id=c and product_id=pid)
    or exists(select 1 from dpq.operations where company_id=c and action not in ('catalog_product','catalog_manage')
       and jsonb_path_exists(payload,'$.** ? (@ == $pid)',jsonb_build_object('pid',pid::text)))
    or exists(select 1 from dpq.workspace_records where company_id=c
       and jsonb_path_exists(data,'$.** ? (@ == $pid)',jsonb_build_object('pid',pid::text)));
   if reference_exists then raise exception 'DPQ_PRODUCT_HISTORY';end if;
   delete from public.inventory where company_id=c and product_id=pid and quantity=0;
   delete from public.products where company_id=c and id=pid;
  else
   update public.products set active=false where company_id=c and id=pid;
  end if;
 elsif op='restore' then
  if exists(select 1 from public.products where company_id=c and id<>pid and dpq.clean_barcode(barcode)=dpq.clean_barcode(p.barcode)) then raise exception 'DPQ_BARCODE_DUPLICATE';end if;
  update public.products set active=true where company_id=c and id=pid;
 end if;
 -- Preserve the old card in the audit trail even for a never-used product deletion.
 insert into dpq.audit(company_id,actor,action,payload) values(c,u,'catalog_'||op,jsonb_build_object('product_id',pid,'before',case when p.id is null then null else to_jsonb(p) end));
 return jsonb_build_object('id',pid,'operation',op);
end $$;
revoke all on function dpq.catalog_change(uuid,uuid,text,jsonb) from public,anon,authenticated;

do $migration$
declare source text; revised text; start_at integer; end_at integer;
begin
 select pg_get_functiondef('public.dpq_call(text,jsonb,text)'::regprocedure) into source;
 if position('dpq.catalog_change' in source)>0 then return;end if;
 revised:=replace(source,'''catalog_product'',''catalog_location''','''catalog_product'',''catalog_manage'',''catalog_location''');
 revised:=replace(revised,'''catalog_product'',''support''','''catalog_product'',''catalog_manage'',''support''');
 revised:=replace(revised,'if pid is not null and not exists','if p_action<>''catalog_manage'' and pid is not null and not exists');
 revised:=replace(revised,'''products'',coalesce(','''catalog_aliases'',coalesce((select jsonb_agg(jsonb_build_object(''id'',payload->>''product_id'',''barcode'',payload->''before''->>''barcode'') order by created_at) from dpq.audit where company_id=c and action=''catalog_edit'' and payload->''before''->>''barcode'' is not null),''[]''),''products'',coalesce(');
 start_at:=position('elsif p_action=''catalog_product'' then' in revised);
 end_at:=position('elsif p_action=''catalog_location'' then' in revised);
 if start_at=0 or end_at<=start_at or revised=source then raise exception 'Catalog migration: unexpected RPC version';end if;
 revised:=substring(revised from 1 for start_at-1)||$patch$
 elsif p_action='catalog_product' then
 result:=dpq.catalog_change(c,u,'legacy_save',p_payload);
 elsif p_action='catalog_manage' then
 result:=dpq.catalog_change(c,u,p_payload->>'operation',p_payload);
 $patch$||substring(revised from end_at);
 execute revised;
end $migration$;

create or replace function public.dpq_0271_ready() returns text language sql security invoker set search_path='' as $$ select '0.27.1'::text $$;
revoke all on function public.dpq_0271_ready() from public,anon;
grant execute on function public.dpq_0271_ready() to authenticated;
