begin;
-- Reviewed metadata export: client roles must not hold table-wide DDL privileges.
-- Keep existing SELECT/INSERT/UPDATE/DELETE and RLS policies unchanged.
do $$ declare t text; begin
 foreach t in array array['cloud_devices','cloud_operations','companies','company_members',
 'company_subscriptions','inventory','locations','product_change_requests','products',
 'profiles','stock_movements','sync_events'] loop
 if to_regclass('public.'||t) is not null then
 execute format('revoke truncate, references, trigger on table public.%I from public, anon, authenticated',t);
 end if;
 end loop;
end $$;
commit;
