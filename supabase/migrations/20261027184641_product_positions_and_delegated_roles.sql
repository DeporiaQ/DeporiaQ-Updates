-- 0.28.1: text-only product positions, reversible offer removal, delegated roles.
-- Owner identities, stock quantities, subscriptions and historical receipts are unchanged.
alter table dpq.retail_offers add column if not exists deleted_at timestamptz;
create table if not exists dpq.product_positions(
 company_id uuid not null references public.companies(id),id uuid not null default gen_random_uuid(),
 location_id uuid not null references public.locations(id),product_id uuid not null references public.products(id),
 floor text not null default '',area text not null default '',shelf text not null,compartment text not null default '',note text not null default '',
 version integer not null default 1,actor uuid not null,updated_at timestamptz not null default now(),primary key(company_id,id)
);
create index if not exists product_positions_lookup on dpq.product_positions(company_id,product_id,location_id);
create table if not exists dpq.role_delegations(
 company_id uuid not null references public.companies(id),user_id uuid not null,role text not null check(role in ('admin','manager','employee','warehouse','branch','viewer')),
 expires_at timestamptz,version integer not null default 1,actor uuid not null,updated_at timestamptz not null default now(),primary key(company_id,user_id)
);
alter table dpq.product_positions enable row level security;
alter table dpq.role_delegations enable row level security;
revoke all on dpq.product_positions,dpq.role_delegations from public,anon,authenticated;
-- Preserve only physically confirmed legacy addresses; generated proposals stay outside search.
insert into dpq.product_positions(company_id,id,location_id,product_id,floor,shelf,actor)
select s.company_id,md5(s.company_id::text||s.location_id::text||s.product_id::text||s.rack||s.level::text)::uuid,
 s.location_id,s.product_id,s.level::text,s.rack,l.actor
from dpq.rack_stock s join dpq.rack_layouts l using(company_id,location_id) where s.verified
on conflict do nothing;
create or replace function dpq.effective_role(c uuid,u uuid) returns text
language sql stable security invoker set search_path='' as $$
 select case when m.role='owner' then 'owner' else coalesce((select d.role from dpq.role_delegations d where d.company_id=c and d.user_id=u and (d.expires_at is null or d.expires_at>statement_timestamp())),m.role) end
 from public.company_members m where m.company_id=c and m.user_id=u and m.active
$$;
revoke all on function dpq.effective_role(uuid,uuid) from public,anon,authenticated;
-- Install effective-role checks at the server entry point and catalog guard, not in clients.
do $$ declare definition text;begin
 definition:=pg_get_functiondef('public.dpq_call(text,jsonb,text)'::regprocedure);
 if position('role_name:=dpq.effective_role(c,u);' in definition)=0 then
  if position('admin:=role_name in' in definition)=0 then raise exception 'Unexpected dpq_call definition';end if;
  definition:=replace(definition,'admin:=role_name in','role_name:=dpq.effective_role(c,u); admin:=role_name in');execute definition;
 end if;
 definition:=pg_get_functiondef('dpq.catalog_change(uuid,uuid,text,jsonb)'::regprocedure);
 if position('role_name:=dpq.effective_role(c,u);' in definition)=0 then
  definition:=replace(definition,'if role_name is null or role_name not in','role_name:=dpq.effective_role(c,u); if role_name is null or role_name not in');execute definition;
 end if;
end $$;
create or replace function dpq.retail_can(c uuid,u uuid,d text,r text,cap text) returns boolean
language sql stable security invoker set search_path='' as $$
 select r='owner' or (r='admin' and (cap in ('layout','finance','customers') or exists(select 1 from dpq.role_delegations x where x.company_id=c and x.user_id=u and x.role='admin' and (x.expires_at is null or x.expires_at>statement_timestamp()))))
 or exists(select 1 from dpq.retail_grants where company_id=c and user_id=u and device=d and capability=cap)
$$;
-- Keep the tested 0.28 engine private, expose one authenticated dispatcher.
do $$ begin
 if to_regprocedure('dpq.retail_0280(text,jsonb,text)') is null then
  alter function public.dpq_retail(text,jsonb,text) set schema dpq;
  alter function dpq.dpq_retail(text,jsonb,text) rename to retail_0280;
 end if;
end $$;
revoke all on function dpq.retail_0280(text,jsonb,text) from public,anon,authenticated;
create or replace function public.dpq_retail(p_action text,p_payload jsonb default '{}',p_device text default '') returns jsonb
language plpgsql security definer set search_path='' as $$
declare s jsonb;c uuid;u uuid:=auth.uid();r text;owner_ok boolean;req uuid;prior dpq.operations%rowtype;result jsonb;
 idv uuid;lid uuid;pid uuid;v integer;namev text;target_role text;expiry timestamptz;row_old dpq.product_positions%rowtype;body jsonb;
begin
 if u is null then raise exception 'DPQ_AUTH';end if;
 s:=public.dpq_call('status','{}',p_device);c:=(s->>'company_id')::uuid;r:=s->>'role';
 if not coalesce((s->>'allowed')::boolean,false) or not coalesce((s->>'enabled')::boolean,false) then raise exception 'DPQ_LICENSE';end if;
 if not exists(select 1 from dpq.devices where company_id=c and code=p_device and user_id=u and active) then raise exception 'DPQ_DEVICE';end if;
 if jsonb_typeof(p_payload) is distinct from 'object' or octet_length(p_payload::text)>300000 then raise exception 'DPQ_INPUT';end if;
 perform 1 from dpq.settings where company_id=c for update;
 owner_ok:=exists(select 1 from public.company_members where company_id=c and user_id=u and active and role='owner');
 if p_action='retail_snapshot' then
  result:=dpq.retail_0280(p_action,p_payload,p_device);
  return (result-'layouts'-'shelves')||jsonb_build_object('offers',coalesce((select jsonb_agg(x) from jsonb_array_elements(result->'offers') x where x->>'deleted_at' is null),'[]'),'positions',coalesce((select jsonb_agg(to_jsonb(x)) from dpq.product_positions x where company_id=c),'[]'),'can_manage_team',owner_ok);
 elsif p_action='retail_team' then
  if not owner_ok then raise exception 'DPQ_OWNER: Yetkileri yalnız ana yönetici değiştirebilir';end if;
  return jsonb_build_object('members',coalesce((select jsonb_agg(jsonb_build_object('user_id',m.user_id,'base_role',m.role,'effective_role',dpq.effective_role(c,m.user_id),'name',coalesce((select display_name from dpq.user_directory ud where ud.company_id=c and ud.user_id=m.user_id),(select max(d.name) from dpq.devices d where d.company_id=c and d.user_id=m.user_id),m.user_id::text),'delegation',to_jsonb(g))) from public.company_members m left join dpq.role_delegations g on g.company_id=m.company_id and g.user_id=m.user_id where m.company_id=c and m.active),'[]'),'locations',coalesce((select jsonb_agg(to_jsonb(l)) from public.locations l where company_id=c and active),'[]'),'assignments',coalesce((select jsonb_agg(to_jsonb(a)) from dpq.staff_locations a where company_id=c),'[]'));
 elsif p_action in ('retail_layout_save','retail_shelf_place','retail_seed_layouts') then
  raise exception 'DPQ_INPUT: Raf görselleri kaldırıldı. Ürün Konumları ekranını kullanın';
 elsif p_action not in ('retail_offer_delete','retail_position_save','retail_position_delete','retail_role_save') then
  if p_action='retail_offer_save' and exists(select 1 from dpq.retail_offers where company_id=c and id=(p_payload->>'id')::uuid and deleted_at is not null) then raise exception 'DPQ_CONFLICT: Bu kayıt silindi';end if;
  return dpq.retail_0280(p_action,p_payload,p_device);
 end if;
 req:=(p_payload->>'request_id')::uuid;if req is null then raise exception 'DPQ_REQUEST';end if;
 select * into prior from dpq.operations where company_id=c and request_id=req;
 if found then
  if prior.action<>p_action or prior.payload<>p_payload or prior.actor<>u then raise exception 'DPQ_REPLAY';end if;return prior.result;
 end if;
 idv:=coalesce(nullif(p_payload->>'id','')::uuid,req);
 if p_action='retail_offer_delete' then
  if not dpq.retail_can(c,u,p_device,r,'offers') then raise exception 'DPQ_ROLE';end if;
  update dpq.retail_offers set deleted_at=clock_timestamp(),active=false,version=version+1 where company_id=c and id=idv and version=(p_payload->>'version')::integer and deleted_at is null;
  if not found then raise exception 'DPQ_CONFLICT: Kayıt değişti veya silindi';end if;result:=jsonb_build_object('deleted',true,'id',idv);
 elsif p_action in ('retail_position_save','retail_position_delete') then
  if not dpq.retail_can(c,u,p_device,r,'layout') then raise exception 'DPQ_ROLE';end if;
  select * into row_old from dpq.product_positions where company_id=c and id=idv;
  if row_old.id is not null and row_old.version<>coalesce((p_payload->>'version')::integer,0) then raise exception 'DPQ_CONFLICT';end if;
  if row_old.id is null and p_payload ? 'id' then raise exception 'DPQ_CONFLICT';end if;
  if p_action='retail_position_delete' then
   delete from dpq.product_positions where company_id=c and id=idv;if not found then raise exception 'DPQ_CONFLICT';end if;result:=jsonb_build_object('deleted',true);
  else
   body:=p_payload->'data';lid:=(body->>'location_id')::uuid;pid:=(body->>'product_id')::uuid;
   if not exists(select 1 from public.locations where company_id=c and id=lid and active) or not exists(select 1 from public.products where company_id=c and id=pid and active) then raise exception 'DPQ_INPUT';end if;
   if length(trim(coalesce(body->>'shelf',''))) not between 1 and 100 or exists(select 1 from jsonb_each_text(body) x where length(x.value)>500) then raise exception 'DPQ_INPUT: Raf adı gerekli; alanlar en fazla 500 karakter olabilir';end if;
   insert into dpq.product_positions(company_id,id,location_id,product_id,floor,area,shelf,compartment,note,actor)
   values(c,idv,lid,pid,trim(coalesce(body->>'floor','')),trim(coalesce(body->>'area','')),trim(body->>'shelf'),trim(coalesce(body->>'compartment','')),trim(coalesce(body->>'note','')),u)
   on conflict(company_id,id) do update set location_id=excluded.location_id,product_id=excluded.product_id,floor=excluded.floor,area=excluded.area,shelf=excluded.shelf,compartment=excluded.compartment,note=excluded.note,actor=u,version=dpq.product_positions.version+1,updated_at=clock_timestamp();
   select to_jsonb(x) into result from dpq.product_positions x where company_id=c and id=idv;
  end if;
 elsif p_action='retail_role_save' then
  if not owner_ok then raise exception 'DPQ_OWNER: Yetki devrini yalnız ana yönetici yapabilir';end if;
  idv:=(p_payload->>'user_id')::uuid;
  if idv=u or not exists(select 1 from public.company_members where company_id=c and user_id=idv and active and role<>'owner') then raise exception 'DPQ_OWNER: Ana yönetici kimliği değiştirilemez';end if;
  select coalesce(max(version),0) into v from dpq.role_delegations where company_id=c and user_id=idv;
  if v<>coalesce((p_payload->>'version')::integer,0) then raise exception 'DPQ_CONFLICT';end if;
  if coalesce((p_payload->>'revoke')::boolean,false) then
   update dpq.role_delegations set expires_at=clock_timestamp(),version=version+1,actor=u,updated_at=clock_timestamp() where company_id=c and user_id=idv;
  else
   target_role:=p_payload->>'role';expiry:=nullif(p_payload->>'expires_at','')::timestamptz;
   if target_role is null or target_role not in ('admin','manager','employee','warehouse','branch','viewer') or expiry<=clock_timestamp() then raise exception 'DPQ_INPUT: Geçerli rol ve gelecek bir bitiş tarihi seçin';end if;
   insert into dpq.role_delegations(company_id,user_id,role,expires_at,actor) values(c,idv,target_role,expiry,u)
   on conflict(company_id,user_id) do update set role=excluded.role,expires_at=excluded.expires_at,version=dpq.role_delegations.version+1,actor=u,updated_at=clock_timestamp();
  end if;
  result:=jsonb_build_object('saved',true,'user_id',idv);
 end if;
 insert into dpq.operations(company_id,request_id,actor,action,payload,result) values(c,req,u,p_action,p_payload,result);
 insert into dpq.audit(company_id,actor,action,payload) values(c,u,p_action,p_payload-'data');
 return result;
end $$;
revoke all on function public.dpq_retail(text,jsonb,text) from public,anon;
grant execute on function public.dpq_retail(text,jsonb,text) to authenticated;
create or replace function public.dpq_0281_ready() returns text language sql security invoker set search_path='' as $$select '0.28.1'::text$$;
revoke all on function public.dpq_0281_ready() from public,anon;
grant execute on function public.dpq_0281_ready() to authenticated;
