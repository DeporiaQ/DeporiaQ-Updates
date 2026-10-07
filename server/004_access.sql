begin;
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
