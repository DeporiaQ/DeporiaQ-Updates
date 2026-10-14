-- User-scoped dispatch leases. SMTP credentials remain in Edge Function secrets.
begin;
create or replace function public.dpq_claim_own_support(p_ticket uuid)
returns jsonb language plpgsql security definer set search_path='' as $$
declare ticket dpq.tickets%rowtype;token uuid:=gen_random_uuid();
begin
 if auth.uid() is null then raise exception 'DPQ_AUTH: Oturum gerekli';end if;
 select t.* into ticket from dpq.tickets t join public.company_members m on m.company_id=t.company_id and m.user_id=auth.uid() and m.active
 where t.id=p_ticket and t.actor=auth.uid() and t.mail_status<>'sent' and t.available_at<=clock_timestamp() and t.attempts<10
 for update of t skip locked;
 if not found then return null;end if;
 update dpq.tickets set lease=token,attempts=attempts+1,available_at=clock_timestamp()+interval '5 minutes' where id=ticket.id;
 return to_jsonb(ticket)||jsonb_build_object('lease',token);
end $$;
create or replace function public.dpq_support_status()
returns jsonb language plpgsql security definer set search_path='' as $$
begin
 if auth.uid() is null then raise exception 'DPQ_AUTH: Oturum gerekli';end if;
 return coalesce((select jsonb_agg(jsonb_build_object('id',t.id,'subject',t.subject,'mail_status',t.mail_status,'created_at',t.created_at,'attempts',t.attempts,'available_at',t.available_at) order by t.created_at desc)
 from dpq.tickets t where t.actor=auth.uid() and exists(select 1 from public.company_members m where m.company_id=t.company_id and m.user_id=auth.uid() and m.active)),'[]');
end $$;
revoke all on function public.dpq_claim_own_support(uuid),public.dpq_support_status() from public,anon;
grant execute on function public.dpq_claim_own_support(uuid),public.dpq_support_status() to authenticated;
commit;
