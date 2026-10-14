-- Live sessions are separate from licensed device registrations.
begin;
create table if not exists dpq.user_directory (
 company_id uuid not null references public.companies(id),user_id uuid not null,display_name text not null,
 primary key(company_id,user_id)
);
alter table dpq.user_directory enable row level security;
revoke all on dpq.user_directory from public,anon,authenticated;
create table if not exists dpq.presence (
 company_id uuid not null references public.companies(id),
 user_id uuid not null, device text not null, session_id uuid not null,
 display_name text not null, seen_at timestamptz not null default clock_timestamp(),
 primary key(company_id,user_id,device,session_id)
);
alter table dpq.presence enable row level security;
revoke all on dpq.presence from public,anon,authenticated;
create or replace function public.dpq_presence(p_device text,p_session uuid,p_name text default '',p_leave boolean default false)
returns jsonb language plpgsql security definer set search_path='' as $$
declare c uuid;u uuid:=auth.uid();
begin
 if u is null or (select count(*) from public.company_members where user_id=u and active)<>1 then raise exception 'DPQ_AUTH: Etkin üyelik gerekli'; end if;
 select company_id into c from public.company_members where user_id=u and active;
 if p_session is null then raise exception 'DPQ_SESSION: Oturum kimliği gerekli'; end if;
 if p_leave then
  delete from dpq.presence where company_id=c and user_id=u and device=p_device and session_id=p_session;
 else
  if not exists(select 1 from public.company_subscriptions where company_id=c and status in ('active','trial','past_due') and valid_until>clock_timestamp()) then raise exception 'DPQ_LICENSE: Abonelik aktif değil'; end if;
  if not exists(select 1 from dpq.devices where company_id=c and code=p_device and active) then raise exception 'DPQ_DEVICE: Etkin cihaz gerekli'; end if;
  if length(trim(p_name)) not between 1 and 100 then raise exception 'DPQ_INPUT: Kullanıcı adı gerekli'; end if;
  insert into dpq.user_directory values(c,u,trim(p_name)) on conflict(company_id,user_id) do update set display_name=excluded.display_name;
  insert into dpq.presence values(c,u,p_device,p_session,trim(p_name),clock_timestamp())
  on conflict(company_id,user_id,device,session_id) do update set seen_at=excluded.seen_at,display_name=excluded.display_name;
 end if;
 delete from dpq.presence where company_id=c and seen_at<clock_timestamp()-interval '30 seconds';
 return coalesce((select jsonb_agg(jsonb_build_object('user_id',x.user_id,'name',x.display_name)) from
 (select distinct on (p.user_id) p.user_id,p.display_name from dpq.presence p
 join public.company_members m on m.company_id=p.company_id and m.user_id=p.user_id and m.active
 join dpq.devices d on d.company_id=p.company_id and d.code=p.device and d.active
 where p.company_id=c and p.seen_at>clock_timestamp()-interval '30 seconds'
 order by p.user_id,p.seen_at desc) x),'[]');
end $$;
revoke all on function public.dpq_presence(text,uuid,text,boolean) from public,anon;
grant execute on function public.dpq_presence(text,uuid,text,boolean) to authenticated;
commit;
