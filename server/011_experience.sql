-- 0.26: owner-only company profile, scoped search and bounded assistant access.
begin;
-- Clients rename companies only through the audited RPC below.
revoke update on public.companies from public,anon,authenticated;
revoke update (name) on public.companies from public,anon,authenticated;

create or replace function public.dpq_company_profile(p_device text,p_name text default null,p_expected_name text default null)
returns jsonb language plpgsql security definer set search_path='' as $$
declare s jsonb;c uuid;n text;old_name text;
begin
 s:=public.dpq_call('status','{}',p_device);c:=(s->>'company_id')::uuid;
 if not coalesce((s->>'enabled')::boolean,false) then raise exception 'DPQ_NOT_READY';end if;
 if not exists(select 1 from dpq.devices where company_id=c and code=p_device and active) then raise exception 'DPQ_DEVICE';end if;
 select name into old_name from public.companies where id=c for update;
 if p_name is not null then
  if s->>'role' is distinct from 'owner' then raise exception 'DPQ_OWNER: Only the business owner can change the company name';end if;
  if not coalesce((s->>'allowed')::boolean,false) then raise exception 'DPQ_LICENSE';end if;
  n:=btrim(p_name);
  if char_length(n) not between 2 and 120 or n ~ '[[:cntrl:]]' then raise exception 'DPQ_INPUT: Company name must contain 2 to 120 characters';end if;
  -- Idempotent retry after a lost response, without overwriting a newer edit.
  if old_name is distinct from n then
   if p_expected_name is distinct from old_name then raise exception 'DPQ_CONFLICT: Company name changed; reopen settings';end if;
   update public.companies set name=n where id=c;
   insert into dpq.audit(company_id,actor,action,payload) values(c,auth.uid(),'company_rename',jsonb_build_object('before',old_name,'after',n));
  end if;
  old_name:=n;
 end if;
 return jsonb_build_object('company_id',c,'name',old_name,'can_rename',s->>'role'='owner');
end $$;
revoke all on function public.dpq_company_profile(text,text,text) from public,anon;
grant execute on function public.dpq_company_profile(text,text,text) to authenticated;

create or replace function dpq.search_fold(value text) returns text language sql immutable set search_path='' as $$
 select lower(translate(coalesce(value,''),'İIıŞşĞğÜüÖöÇç','iiiSsggUuOoCc'))
$$;
create or replace function public.dpq_search(p_query text,p_device text)
returns jsonb language plpgsql security definer set search_path='' as $$
declare s jsonb;c uuid;q text;result jsonb;
begin
 if char_length(btrim(p_query)) not between 2 and 120 then return '[]'::jsonb;end if;
 s:=public.dpq_call('status','{}',p_device);c:=(s->>'company_id')::uuid;
 if not coalesce((s->>'allowed')::boolean,false) or not coalesce((s->>'enabled')::boolean,false) then raise exception 'DPQ_LICENSE';end if;
 if not exists(select 1 from dpq.devices where company_id=c and code=p_device and active) then raise exception 'DPQ_DEVICE';end if;
 q:=dpq.search_fold(btrim(p_query));
 select coalesce(jsonb_agg(to_jsonb(x)),'[]') into result from (
  select * from (
   select 'product'::text kind,p.id,p.name title,p.barcode subtitle,
     case when dpq.search_fold(p.barcode)=q then 0 when dpq.search_fold(p.name)=q then 1 else 2 end rank
   from public.products p where p.company_id=c and p.active and (
    strpos(dpq.search_fold(p.name||' '||p.barcode),q)>0 or exists(
     select 1 from dpq.workspace_records w where w.company_id=c and w.kind='product' and w.data->>'product_id'=p.id::text
     and strpos(dpq.search_fold(concat_ws(' ',w.data->>'author',w.data->>'publisher',w.data->>'category',w.data->>'tags',w.data->>'shelf',w.data->>'brand')),q)>0))
   union all
   select 'location',l.id,l.name,l.location_type,3 from public.locations l
    where l.company_id=c and l.active and strpos(dpq.search_fold(l.name),q)>0
  ) matches order by rank,title,id limit 30
 ) x;
 return result;
end $$;
revoke all on function public.dpq_search(text,text) from public,anon;
grant execute on function public.dpq_search(text,text) to authenticated;

create table if not exists dpq.assistant_usage (
 company_id uuid not null references public.companies(id),user_id uuid not null,
 usage_day date not null,requests integer not null default 0,last_request timestamptz,
 primary key(company_id,user_id,usage_day)
);
alter table dpq.assistant_usage enable row level security;
revoke all on dpq.assistant_usage from public,anon,authenticated;
-- The edge service alone can consume quota, after validating the user's JWT.
create or replace function public.dpq_assistant_access(p_user uuid,p_device text,p_consume boolean default false)
returns jsonb language plpgsql security definer set search_path='' as $$
declare c uuid;r text;used integer;previous timestamptz;day_utc date:=(clock_timestamp() at time zone 'UTC')::date;
begin
 if p_user is null or (select count(*) from public.company_members where user_id=p_user and active)<>1 then raise exception 'DPQ_AUTH';end if;
 select company_id,role into c,r from public.company_members where user_id=p_user and active;
 if not exists(select 1 from public.company_subscriptions where company_id=c and status in ('active','trial','past_due') and valid_until>clock_timestamp())
 or not exists(select 1 from dpq.settings where company_id=c and enabled) then raise exception 'DPQ_LICENSE';end if;
 if not exists(select 1 from dpq.devices where company_id=c and code=p_device and active) then raise exception 'DPQ_DEVICE';end if;
 -- A company lock makes daily caps atomic across simultaneous devices/users.
 perform 1 from dpq.settings where company_id=c for update;
 if p_consume then
  delete from dpq.assistant_usage where company_id=c and usage_day<day_utc-7;
  insert into dpq.assistant_usage(company_id,user_id,usage_day) values(c,p_user,day_utc) on conflict do nothing;
  select requests,last_request into used,previous from dpq.assistant_usage where company_id=c and user_id=p_user and usage_day=day_utc;
  if used>=50 or (select coalesce(sum(requests),0) from dpq.assistant_usage where company_id=c and usage_day=day_utc)>=200 then raise exception 'DPQ_AI_QUOTA';end if;
  if previous>clock_timestamp()-interval '5 seconds' then raise exception 'DPQ_AI_RATE';end if;
  update dpq.assistant_usage set requests=requests+1,last_request=clock_timestamp() where company_id=c and user_id=p_user and usage_day=day_utc;
 end if;
 return jsonb_build_object('role',r,'daily_limit',50,'company_daily_limit',200);
end $$;
revoke all on function public.dpq_assistant_access(uuid,text,boolean) from public,anon,authenticated;
grant execute on function public.dpq_assistant_access(uuid,text,boolean) to service_role;
create or replace function public.dpq_0260_ready() returns text language sql set search_path='' as $$select '0.26.0'::text$$;
revoke all on function public.dpq_0260_ready() from public;
grant execute on function public.dpq_0260_ready() to anon,authenticated,service_role;
notify pgrst,'reload schema';
commit;
