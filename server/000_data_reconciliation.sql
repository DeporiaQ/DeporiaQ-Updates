-- Read-only aggregate report. No product names, customer records or credentials.
select jsonb_build_object(
 'companies', (select jsonb_agg(jsonb_build_object(
  'id',c.id,'name',c.name,'status',s.status,'plan',s.plan_code,'valid_until',s.valid_until,
  'locations',(select count(*) from public.locations where company_id=c.id and active),
  'products',(select count(*) from public.products where company_id=c.id and active),
  'inventory_rows',(select count(*) from public.inventory where company_id=c.id),
  'total_quantity',(select coalesce(sum(quantity),0) from public.inventory where company_id=c.id),
  'active_devices',(select count(*) from public.cloud_devices where company_id=c.id and active)
 )) from public.companies c left join public.company_subscriptions s on s.company_id=c.id),
 'inventory_anomalies', (select count(*) from public.inventory i
 left join public.products p on p.id=i.product_id
 left join public.locations l on l.id=i.location_id
 where i.quantity<0 or i.quantity::text in ('NaN','Infinity','-Infinity')
 or p.id is null or l.id is null
 or p.company_id is distinct from i.company_id or l.company_id is distinct from i.company_id)
) as veri_kontrolu;
