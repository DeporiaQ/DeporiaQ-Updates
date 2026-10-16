-- Isolated test additions from the 2026-10-08 structural export; no customer data.
create table public.stock_movements(id uuid primary key default gen_random_uuid(),company_id uuid references companies(id),location_id uuid references locations(id),product_id uuid references products(id),movement_type text,quantity numeric,unit_price numeric,note text,device_id text,created_by uuid);
create table public.cloud_operations(id uuid primary key default gen_random_uuid(),company_id uuid references companies(id),operation_key text,operation_type text,product_id uuid references products(id),source_location_id uuid references locations(id),target_location_id uuid references locations(id),quantity numeric check(quantity>0),device_id text,note text,created_by uuid,unique(company_id,operation_key));
alter table public.company_members add constraint company_members_role_check CHECK ((role = ANY (ARRAY['owner'::text, 'admin'::text, 'manager'::text, 'employee'::text, 'viewer'::text])));
alter table public.locations add constraint locations_location_type_check CHECK ((location_type = ANY (ARRAY['center'::text, 'warehouse'::text, 'branch'::text])));
alter table public.products add constraint products_critical_stock_check CHECK ((critical_stock >= (0)::numeric));
alter table public.products add constraint products_purchase_price_check CHECK ((purchase_price >= (0)::numeric));
alter table public.products add constraint products_sale_price_check CHECK ((sale_price >= (0)::numeric));
alter table public.stock_movements add constraint stock_movements_movement_type_check CHECK ((movement_type = ANY (ARRAY['initial'::text, 'purchase'::text, 'sale'::text, 'increase'::text, 'decrease'::text, 'transfer_in'::text, 'transfer_out'::text, 'correction'::text, 'return'::text])));
alter table public.company_subscriptions add constraint company_subscriptions_status_check CHECK ((status = ANY (ARRAY['trial'::text, 'active'::text, 'past_due'::text, 'suspended'::text, 'cancelled'::text])));
CREATE OR REPLACE FUNCTION public.is_company_member(target_company uuid)
 RETURNS boolean
 LANGUAGE sql
 STABLE SECURITY DEFINER
 SET search_path TO 'public'
AS $function$
    select exists (
        select 1
        from public.company_members cm
        where cm.company_id = target_company
          and cm.user_id = auth.uid()
          and cm.active = true
    );
$function$
;
CREATE OR REPLACE FUNCTION public.apply_stock_movement(target_company uuid, target_location uuid, target_product uuid, movement_kind text, movement_quantity numeric, movement_unit_price numeric DEFAULT 0, movement_note text DEFAULT NULL::text, source_device text DEFAULT NULL::text)
 RETURNS numeric
 LANGUAGE plpgsql
 SECURITY DEFINER
 SET search_path TO 'public'
AS $function$
declare
    signed_quantity numeric;
    new_quantity numeric;
begin
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
 SET search_path TO 'public'
AS $function$
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
end $function$
;
CREATE OR REPLACE FUNCTION public.apply_stock_transfer_v2(p_company_id uuid, p_product_id uuid, p_source_location_id uuid, p_target_location_id uuid, p_quantity numeric, p_operation_key text, p_device_id text DEFAULT NULL::text, p_note text DEFAULT NULL::text)
 RETURNS jsonb
 LANGUAGE plpgsql
 SECURITY DEFINER
 SET search_path TO 'public'
AS $function$
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
end $function$
;
CREATE OR REPLACE FUNCTION public.get_my_entitlement()
 RETURNS TABLE(company_id uuid, status text, valid_until timestamp with time zone, grace_until timestamp with time zone, plan_code text, allowed boolean, server_time timestamp with time zone)
 LANGUAGE sql
 STABLE SECURITY DEFINER
 SET search_path TO 'public'
AS $function$
  select s.company_id, s.status, s.valid_until, s.grace_until, s.plan_code,
         (
           (s.status in ('trial','active') and now() <= s.valid_until)
           or (s.status='past_due' and s.grace_until is not null and now() <= s.grace_until)
         ) as allowed,
         now() as server_time
  from public.company_subscriptions s
  join public.company_members m on m.company_id=s.company_id
  where m.user_id=auth.uid() and m.active=true
  order by m.created_at asc
  limit 1;
$function$
;
CREATE OR REPLACE FUNCTION public.subscription_allows(p_company_id uuid)
 RETURNS boolean
 LANGUAGE sql
 STABLE SECURITY DEFINER
 SET search_path TO 'public'
AS $function$
  select exists (
    select 1 from public.company_subscriptions s
    where s.company_id=p_company_id and (
      (s.status in ('trial','active') and now() <= s.valid_until)
      or (s.status='past_due' and s.grace_until is not null and now() <= s.grace_until)
    )
  );
$function$
;
