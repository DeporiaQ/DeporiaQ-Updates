-- Old entry points must obey the same verified, one-company enrollment rules.
-- No customer records, subscription periods, Auth users or sessions are changed.
begin;
create or replace function public.create_company(company_name text)
returns uuid language sql security invoker set search_path='' as $$
 select (public.dpq_enroll(company_name)->>'company_id')::uuid
$$;
revoke all on function public.create_company(text) from public,anon;
grant execute on function public.create_company(text) to authenticated,service_role;

do $$ declare signature text; target regprocedure; begin
 foreach signature in array array[
  'public.apply_stock_movement(uuid,uuid,uuid,text,numeric,numeric,text,text)',
  'public.has_company_role(uuid,text[])','public.is_company_member(uuid)'
 ] loop
  target:=to_regprocedure(signature);
  if target is not null then
   execute format('revoke all on function %s from public,anon',target);
   execute format('grant execute on function %s to authenticated,service_role',target);
  end if;
 end loop;
 foreach signature in array array['public.handle_new_user()','public.rls_auto_enable()'] loop
  target:=to_regprocedure(signature);
  if target is not null then execute format('revoke all on function %s from public,anon,authenticated',target);end if;
 end loop;
 if to_regprocedure('public.set_updated_at()') is not null then
  alter function public.set_updated_at() set search_path='';
 end if;
end $$;

create index if not exists dpq_checkout_company_created on dpq.checkout_orders(company_id,created_at);
create index if not exists dpq_checkout_offer on dpq.checkout_orders(offer);
create index if not exists dpq_offers_plan on dpq.offers(plan);
notify pgrst,'reload schema';
commit;
