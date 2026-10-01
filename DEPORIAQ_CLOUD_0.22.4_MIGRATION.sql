-- DeporiaQ 0.22.4 - sunucu taraflı abonelik/lisans denetimi
-- Supabase > SQL Editor > New query içinde BİR KEZ çalıştırın.

create table if not exists public.company_subscriptions (
  company_id uuid primary key references public.companies(id) on delete cascade,
  status text not null default 'trial'
    check (status in ('trial','active','past_due','suspended','cancelled')),
  valid_until timestamptz not null default (now() + interval '14 days'),
  grace_until timestamptz,
  plan_code text not null default 'standard',
  updated_at timestamptz not null default now()
);

alter table public.company_subscriptions enable row level security;
revoke all on table public.company_subscriptions from anon, authenticated;

-- Mevcut işletmelerin çalışması kesilmesin: ilk kurulumda 1 yıllık aktif kayıt açılır.
insert into public.company_subscriptions(company_id,status,valid_until,plan_code)
select id,'active',now() + interval '1 year','standard'
from public.companies
on conflict (company_id) do nothing;

create or replace function public.get_my_entitlement()
returns table (
  company_id uuid,
  status text,
  valid_until timestamptz,
  grace_until timestamptz,
  plan_code text,
  allowed boolean,
  server_time timestamptz
)
language sql
stable
security definer
set search_path = public
as $$
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
$$;

revoke all on function public.get_my_entitlement() from public, anon;
grant execute on function public.get_my_entitlement() to authenticated;

-- Eski uygulama sürümleri de abonelik sona erince Cloud verisini okuyup yazamasın.
create or replace function public.subscription_allows(p_company_id uuid)
returns boolean
language sql
stable
security definer
set search_path = public
as $$
  select exists (
    select 1 from public.company_subscriptions s
    where s.company_id=p_company_id and (
      (s.status in ('trial','active') and now() <= s.valid_until)
      or (s.status='past_due' and s.grace_until is not null and now() <= s.grace_until)
    )
  );
$$;

revoke all on function public.subscription_allows(uuid) from public, anon;
grant execute on function public.subscription_allows(uuid) to authenticated;

do $$
declare t text;
begin
  foreach t in array array[
    'locations','products','inventory','stock_movements','cloud_devices',
    'cloud_operations','sync_events','product_change_requests'
  ] loop
    if to_regclass('public.' || t) is not null then
      execute format('drop policy if exists deporiaq_active_subscription on public.%I', t);
      execute format(
        'create policy deporiaq_active_subscription on public.%I as restrictive for all to authenticated using (public.subscription_allows(company_id)) with check (public.subscription_allows(company_id))',
        t
      );
    end if;
  end loop;
end $$;

-- ÖRNEK YÖNETİM KOMUTLARI (şirket kimliğini kendi kaydınızla değiştirin):
-- Aboneliği 30 gün uzat:
-- update public.company_subscriptions set status='active', valid_until=now()+interval '30 days', updated_at=now() where company_id='...';
-- Erişimi hemen durdur:
-- update public.company_subscriptions set status='suspended', updated_at=now() where company_id='...';
