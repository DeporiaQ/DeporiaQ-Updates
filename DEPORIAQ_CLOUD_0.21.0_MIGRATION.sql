-- DeporiaQ 0.21.0: aktif kullanıcı görünürlüğü ve ürün düzenleme onayları
alter table public.cloud_devices add column if not exists local_username text;
alter table public.cloud_devices add column if not exists location_name text;

create table if not exists public.product_change_requests (
  id uuid primary key default gen_random_uuid(),
  company_id uuid not null references public.companies(id) on delete cascade,
  old_name text not null,
  old_barcode text not null,
  new_name text not null,
  new_barcode text not null,
  requester_name text not null,
  requested_by uuid not null,
  status text not null default 'pending' check (status in ('pending','approved','rejected')),
  created_at timestamptz not null default now(),
  decided_at timestamptz,
  decided_by uuid
);
alter table public.product_change_requests enable row level security;
drop policy if exists "company members read product requests" on public.product_change_requests;
create policy "company members read product requests" on public.product_change_requests for select using (
  exists(select 1 from public.company_members m where m.company_id=product_change_requests.company_id and m.user_id=auth.uid() and m.active=true)
);
drop policy if exists "company members create product requests" on public.product_change_requests;
create policy "company members create product requests" on public.product_change_requests for insert with check (
  requested_by=auth.uid() and exists(select 1 from public.company_members m where m.company_id=product_change_requests.company_id and m.user_id=auth.uid() and m.active=true)
);
drop policy if exists "company managers decide product requests" on public.product_change_requests;
create policy "company managers decide product requests" on public.product_change_requests for update using (
  exists(select 1 from public.company_members m where m.company_id=product_change_requests.company_id and m.user_id=auth.uid() and m.active=true and m.role in ('owner','admin','manager'))
);
