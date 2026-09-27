-- DeporiaQ 0.22.0 için salt-okunur Cloud üyelik kontrolü.
-- Supabase > SQL Editor > New query alanında çalıştırabilirsiniz.
select
  u.email,
  c.name as isletme,
  cm.role,
  cm.active
from public.company_members cm
join auth.users u on u.id = cm.user_id
join public.companies c on c.id = cm.company_id
order by u.email;
