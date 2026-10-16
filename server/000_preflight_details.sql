-- Read-only structural report; no customer rows or credentials are selected.
select jsonb_build_object(
 'functions', (select jsonb_agg(jsonb_build_object(
   'name',p.proname,'definition',pg_get_functiondef(p.oid)))
   from pg_proc p join pg_namespace n on n.oid=p.pronamespace
   where n.nspname='public' and p.prokind='f'),
 'constraints', (select jsonb_agg(jsonb_build_object(
   'table',c.relname,'name',k.conname,'definition',pg_get_constraintdef(k.oid)))
   from pg_constraint k join pg_class c on c.oid=k.conrelid
   join pg_namespace n on n.oid=c.relnamespace
   where n.nspname='public'),
 'triggers', (select jsonb_agg(jsonb_build_object(
   'table',c.relname,'definition',pg_get_triggerdef(t.oid)))
   from pg_trigger t join pg_class c on c.oid=t.tgrelid
   join pg_namespace n on n.oid=c.relnamespace
   where n.nspname='public' and not t.tgisinternal),
 'indexes', (select jsonb_agg(to_jsonb(i)) from
   (select tablename,indexname,indexdef from pg_indexes where schemaname='public') i)
) as ek_rapor;
