-- DeporiaQ 0.12.0 - mevcut 0.11 Cloud şemasına güvenli yükseltme
-- Supabase > SQL Editor ekranında bir kez çalıştırılır. Tekrar çalıştırılması güvenlidir.

create extension if not exists pgcrypto;

create table if not exists public.cloud_operations (
  id uuid primary key default gen_random_uuid(),
  company_id uuid not null references public.companies(id) on delete cascade,
  operation_key text not null,
  operation_type text not null,
  product_id uuid references public.products(id),
  source_location_id uuid references public.locations(id),
  target_location_id uuid references public.locations(id),
  quantity numeric not null check (quantity > 0),
  device_id text,
  note text,
  created_by uuid not null references auth.users(id),
  created_at timestamptz not null default now(),
  unique(company_id, operation_key)
);

alter table public.cloud_operations enable row level security;
drop policy if exists cloud_operations_select_member on public.cloud_operations;
create policy cloud_operations_select_member on public.cloud_operations for select
to authenticated using (exists (
  select 1 from public.company_members cm
  where cm.company_id=cloud_operations.company_id and cm.user_id=auth.uid() and cm.active=true
));

drop policy if exists devices_manage_admin on public.cloud_devices;
create policy devices_manage_admin on public.cloud_devices for update to authenticated
using (exists (select 1 from public.company_members cm where cm.company_id=cloud_devices.company_id
  and cm.user_id=auth.uid() and cm.active=true and cm.role in ('owner','admin')))
with check (exists (select 1 from public.company_members cm where cm.company_id=cloud_devices.company_id
  and cm.user_id=auth.uid() and cm.active=true and cm.role in ('owner','admin')));

create or replace function public.apply_stock_movement_v2(
  p_company_id uuid, p_product_id uuid, p_location_id uuid, p_quantity numeric,
  p_direction text, p_movement_type text, p_operation_key text,
  p_device_id text default null, p_note text default null
) returns numeric language plpgsql security definer set search_path=public as $$
declare v_current numeric; v_new numeric;
begin
  if not exists (select 1 from company_members where company_id=p_company_id and user_id=auth.uid()
    and active=true and role in ('owner','admin','manager','employee')) then raise exception 'Yetkisiz Cloud işlemi'; end if;
  if exists (select 1 from cloud_operations where company_id=p_company_id and operation_key=p_operation_key) then
    select quantity into v_current from inventory where company_id=p_company_id and product_id=p_product_id and location_id=p_location_id;
    return coalesce(v_current,0);
  end if;
  if p_quantity<=0 or p_direction not in ('increase','decrease') then raise exception 'Geçersiz stok hareketi'; end if;
  insert into inventory(company_id,product_id,location_id,quantity) values(p_company_id,p_product_id,p_location_id,0)
    on conflict(company_id,location_id,product_id) do nothing;
  select quantity into v_current from inventory where company_id=p_company_id and product_id=p_product_id and location_id=p_location_id for update;
  v_new := v_current + case when p_direction='increase' then p_quantity else -p_quantity end;
  if v_new<0 then raise exception 'Yetersiz stok'; end if;
  update inventory set quantity=v_new, updated_at=now() where company_id=p_company_id and product_id=p_product_id and location_id=p_location_id;
  insert into cloud_operations(company_id,operation_key,operation_type,product_id,source_location_id,target_location_id,quantity,device_id,note,created_by)
  values(p_company_id,p_operation_key,p_movement_type,p_product_id,
    case when p_direction='decrease' then p_location_id end, case when p_direction='increase' then p_location_id end,
    p_quantity,p_device_id,p_note,auth.uid());
  return v_new;
end $$;

create or replace function public.apply_stock_transfer_v2(
  p_company_id uuid, p_product_id uuid, p_source_location_id uuid, p_target_location_id uuid,
  p_quantity numeric, p_operation_key text, p_device_id text default null, p_note text default null
) returns jsonb language plpgsql security definer set search_path=public as $$
declare v_source numeric; v_target numeric;
begin
  if not exists (select 1 from company_members where company_id=p_company_id and user_id=auth.uid()
    and active=true and role in ('owner','admin','manager','employee')) then raise exception 'Yetkisiz Cloud işlemi'; end if;
  if exists (select 1 from cloud_operations where company_id=p_company_id and operation_key=p_operation_key) then
    select quantity into v_source from inventory where company_id=p_company_id and product_id=p_product_id and location_id=p_source_location_id;
    select quantity into v_target from inventory where company_id=p_company_id and product_id=p_product_id and location_id=p_target_location_id;
    return jsonb_build_object('source',coalesce(v_source,0),'target',coalesce(v_target,0));
  end if;
  if p_quantity<=0 or p_source_location_id=p_target_location_id then raise exception 'Geçersiz transfer'; end if;
  insert into inventory(company_id,product_id,location_id,quantity) values
    (p_company_id,p_product_id,p_source_location_id,0),(p_company_id,p_product_id,p_target_location_id,0)
    on conflict(company_id,location_id,product_id) do nothing;
  perform 1 from inventory where company_id=p_company_id and product_id=p_product_id
    and location_id in (p_source_location_id,p_target_location_id) order by location_id for update;
  select quantity into v_source from inventory where company_id=p_company_id and product_id=p_product_id and location_id=p_source_location_id;
  if v_source<p_quantity then raise exception 'Yetersiz stok'; end if;
  update inventory set quantity=quantity-p_quantity,updated_at=now() where company_id=p_company_id and product_id=p_product_id and location_id=p_source_location_id;
  update inventory set quantity=quantity+p_quantity,updated_at=now() where company_id=p_company_id and product_id=p_product_id and location_id=p_target_location_id returning quantity into v_target;
  insert into cloud_operations(company_id,operation_key,operation_type,product_id,source_location_id,target_location_id,quantity,device_id,note,created_by)
  values(p_company_id,p_operation_key,'TRANSFER',p_product_id,p_source_location_id,p_target_location_id,p_quantity,p_device_id,p_note,auth.uid());
  return jsonb_build_object('source',v_source-p_quantity,'target',v_target);
end $$;

revoke all on function public.apply_stock_movement_v2(uuid,uuid,uuid,numeric,text,text,text,text,text) from public;
revoke all on function public.apply_stock_transfer_v2(uuid,uuid,uuid,uuid,numeric,text,text,text) from public;
grant execute on function public.apply_stock_movement_v2(uuid,uuid,uuid,numeric,text,text,text,text,text) to authenticated;
grant execute on function public.apply_stock_transfer_v2(uuid,uuid,uuid,uuid,numeric,text,text,text) to authenticated;

select 'DeporiaQ Cloud 0.12.0 migration tamamlandı' as sonuc;
