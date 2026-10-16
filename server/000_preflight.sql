-- READ ONLY. Run against test/production to obtain schema evidence before migration.
-- Contains no credentials or customer rows.
select table_name,column_name,data_type,is_nullable from information_schema.columns
where table_schema='public' and table_name in ('companies','company_members','company_subscriptions','locations','products','inventory','cloud_devices')
order by table_name,ordinal_position;
select schemaname,tablename,policyname,permissive,roles,cmd,qual,with_check from pg_policies
where schemaname='public' order by tablename,policyname;
select n.nspname as schema,p.proname as function,pg_get_function_identity_arguments(p.oid) as arguments,
p.prosecdef as security_definer,p.proconfig as settings,p.proacl as grants
from pg_proc p join pg_namespace n on n.oid=p.pronamespace
where n.nspname='public' order by p.proname;
select table_name,grantee,privilege_type from information_schema.role_table_grants
where table_schema='public' and grantee in ('anon','authenticated') order by table_name,grantee;
