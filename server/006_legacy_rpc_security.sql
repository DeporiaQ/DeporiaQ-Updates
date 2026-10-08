begin;
-- Legacy RPCs execute as their owner, so table RLS is not an entitlement check.
create or replace function dpq.check_legacy_stock(c uuid,p uuid,ls uuid[]) returns void
language plpgsql security definer set search_path='' as $$
begin
 if auth.uid() is null then raise exception 'DPQ_AUTH'; end if;
 if not exists(select 1 from public.company_members where company_id=c and user_id=auth.uid() and active and role in ('owner','admin','manager','employee')) then raise exception 'DPQ_ROLE'; end if;
 if exists(select 1 from dpq.settings where company_id=c and enabled) then raise exception 'DPQ_SERVER_ONLY'; end if;
 if not exists(select 1 from public.company_subscriptions where company_id=c and status in ('trial','active','past_due') and valid_until>clock_timestamp()) then raise exception 'DPQ_LICENSE'; end if;
 if not exists(select 1 from public.products where id=p and company_id=c and active) then raise exception 'DPQ_PRODUCT'; end if;
 if ls is null or cardinality(ls)=0 or exists(select 1 from unnest(ls) l where l is null or not exists(select 1 from public.locations where id=l and company_id=c and active)) then raise exception 'DPQ_LOCATION'; end if;
end $$;
revoke all on function dpq.check_legacy_stock(uuid,uuid,uuid[]) from public,anon,authenticated;
CREATE OR REPLACE FUNCTION public.apply_stock_movement(target_company uuid, target_location uuid, target_product uuid, movement_kind text, movement_quantity numeric, movement_unit_price numeric DEFAULT 0, movement_note text DEFAULT NULL::text, source_device text DEFAULT NULL::text)
 RETURNS numeric
 LANGUAGE plpgsql
 SECURITY DEFINER
 SET search_path TO ''
AS $function$
declare
    signed_quantity numeric;
    new_quantity numeric;
begin
 perform dpq.check_legacy_stock(target_company,target_product,array[target_location]);
    if auth.uid() is null then
        raise exception 'Oturum açılması gerekiyor.';
    end if;

    if not public.is_company_member(target_company) then
        raise exception 'Bu işletme için yetkiniz bulunmuyor.';
    end if;

    if movement_quantity is null or movement_quantity <= 0 then
        raise exception 'Miktar sıfırdan büyük olmalıdır.';
    end if;

    if movement_kind in (
        'sale',
        'decrease',
        'transfer_out'
    ) then
        signed_quantity := -movement_quantity;
    elsif movement_kind in (
        'initial',
        'purchase',
        'increase',
        'transfer_in',
        'correction',
        'return'
    ) then
        signed_quantity := movement_quantity;
    else
        raise exception 'Geçersiz stok hareket türü.';
    end if;

    if not exists (
        select 1
        from public.locations
        where id = target_location
          and company_id = target_company
          and active = true
    ) then
        raise exception 'Geçersiz veya pasif konum.';
    end if;

    if not exists (
        select 1
        from public.products
        where id = target_product
          and company_id = target_company
          and active = true
    ) then
        raise exception 'Geçersiz veya pasif ürün.';
    end if;

    insert into public.inventory (
        company_id,
        location_id,
        product_id,
        quantity
    )
    values (
        target_company,
        target_location,
        target_product,
        signed_quantity
    )
    on conflict (company_id, location_id, product_id)
    do update set
        quantity = public.inventory.quantity + excluded.quantity,
        updated_at = now()
    returning quantity into new_quantity;

    if new_quantity < 0 then
        raise exception 'Stok miktarı eksiye düşemez.';
    end if;

    insert into public.stock_movements (
        company_id,
        location_id,
        product_id,
        movement_type,
        quantity,
        unit_price,
        note,
        device_id,
        created_by
    )
    values (
        target_company,
        target_location,
        target_product,
        movement_kind,
        movement_quantity,
        coalesce(movement_unit_price, 0),
        movement_note,
        source_device,
        auth.uid()
    );

    return new_quantity;
end;
$function$
;
CREATE OR REPLACE FUNCTION public.apply_stock_movement_v2(p_company_id uuid, p_product_id uuid, p_location_id uuid, p_quantity numeric, p_direction text, p_movement_type text, p_operation_key text, p_device_id text DEFAULT NULL::text, p_note text DEFAULT NULL::text)
 RETURNS numeric
 LANGUAGE plpgsql
 SECURITY DEFINER
 SET search_path TO ''
AS $function$
declare v_current numeric; v_new numeric;
begin
 perform dpq.check_legacy_stock(p_company_id,p_product_id,array[p_location_id]);
  if not exists (select 1 from public.company_members where company_id=p_company_id and user_id=auth.uid()
    and active=true and role in ('owner','admin','manager','employee')) then raise exception 'Yetkisiz Cloud işlemi'; end if;
  if exists (select 1 from public.cloud_operations where company_id=p_company_id and operation_key=p_operation_key) then
    select quantity into v_current from public.inventory where company_id=p_company_id and product_id=p_product_id and location_id=p_location_id;
    return coalesce(v_current,0);
  end if;
  if p_quantity<=0 or p_direction not in ('increase','decrease') then raise exception 'Geçersiz stok hareketi'; end if;
  insert into public.inventory(company_id,product_id,location_id,quantity) values(p_company_id,p_product_id,p_location_id,0)
    on conflict(company_id,location_id,product_id) do nothing;
  select quantity into v_current from public.inventory where company_id=p_company_id and product_id=p_product_id and location_id=p_location_id for update;
  v_new := v_current + case when p_direction='increase' then p_quantity else -p_quantity end;
  if v_new<0 then raise exception 'Yetersiz stok'; end if;
  update public.inventory set quantity=v_new, updated_at=now() where company_id=p_company_id and product_id=p_product_id and location_id=p_location_id;
  insert into public.cloud_operations(company_id,operation_key,operation_type,product_id,source_location_id,target_location_id,quantity,device_id,note,created_by)
  values(p_company_id,p_operation_key,p_movement_type,p_product_id,
    case when p_direction='decrease' then p_location_id end, case when p_direction='increase' then p_location_id end,
    p_quantity,p_device_id,p_note,auth.uid());
  return v_new;
end $function$
;
CREATE OR REPLACE FUNCTION public.apply_stock_transfer_v2(p_company_id uuid, p_product_id uuid, p_source_location_id uuid, p_target_location_id uuid, p_quantity numeric, p_operation_key text, p_device_id text DEFAULT NULL::text, p_note text DEFAULT NULL::text)
 RETURNS jsonb
 LANGUAGE plpgsql
 SECURITY DEFINER
 SET search_path TO ''
AS $function$
declare v_source numeric; v_target numeric;
begin
 perform dpq.check_legacy_stock(p_company_id,p_product_id,array[p_source_location_id,p_target_location_id]);
  if not exists (select 1 from public.company_members where company_id=p_company_id and user_id=auth.uid()
    and active=true and role in ('owner','admin','manager','employee')) then raise exception 'Yetkisiz Cloud işlemi'; end if;
  if exists (select 1 from public.cloud_operations where company_id=p_company_id and operation_key=p_operation_key) then
    select quantity into v_source from public.inventory where company_id=p_company_id and product_id=p_product_id and location_id=p_source_location_id;
    select quantity into v_target from public.inventory where company_id=p_company_id and product_id=p_product_id and location_id=p_target_location_id;
    return jsonb_build_object('source',coalesce(v_source,0),'target',coalesce(v_target,0));
  end if;
  if p_quantity<=0 or p_source_location_id=p_target_location_id then raise exception 'Geçersiz transfer'; end if;
  insert into public.inventory(company_id,product_id,location_id,quantity) values
    (p_company_id,p_product_id,p_source_location_id,0),(p_company_id,p_product_id,p_target_location_id,0)
    on conflict(company_id,location_id,product_id) do nothing;
  perform 1 from public.inventory where company_id=p_company_id and product_id=p_product_id
    and location_id in (p_source_location_id,p_target_location_id) order by location_id for update;
  select quantity into v_source from public.inventory where company_id=p_company_id and product_id=p_product_id and location_id=p_source_location_id;
  if v_source<p_quantity then raise exception 'Yetersiz stok'; end if;
  update public.inventory set quantity=quantity-p_quantity,updated_at=now() where company_id=p_company_id and product_id=p_product_id and location_id=p_source_location_id;
  update public.inventory set quantity=quantity+p_quantity,updated_at=now() where company_id=p_company_id and product_id=p_product_id and location_id=p_target_location_id returning quantity into v_target;
  insert into public.cloud_operations(company_id,operation_key,operation_type,product_id,source_location_id,target_location_id,quantity,device_id,note,created_by)
  values(p_company_id,p_operation_key,'TRANSFER',p_product_id,p_source_location_id,p_target_location_id,p_quantity,p_device_id,p_note,auth.uid());
  return jsonb_build_object('source',v_source-p_quantity,'target',v_target);
end $function$
;
commit;
