-- DeporiaQ 0.21.2: ürün özelleştirme taleplerinin REST erişim izinleri
-- RLS politikaları erişimi şirket üyeliğiyle sınırlamaya devam eder.
grant usage on schema public to authenticated;
grant select, insert, update on table public.product_change_requests to authenticated;

drop policy if exists "company managers decide product requests" on public.product_change_requests;
create policy "company managers decide product requests"
on public.product_change_requests for update
using (
  exists (
    select 1 from public.company_members m
    where m.company_id=product_change_requests.company_id
      and m.user_id=auth.uid() and m.active=true
      and m.role in ('owner','admin','manager')
  )
)
with check (
  exists (
    select 1 from public.company_members m
    where m.company_id=product_change_requests.company_id
      and m.user_id=auth.uid() and m.active=true
      and m.role in ('owner','admin','manager')
  )
);
