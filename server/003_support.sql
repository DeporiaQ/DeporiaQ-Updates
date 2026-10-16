begin;
alter table dpq.tickets add column if not exists attempts integer not null default 0;
alter table dpq.tickets add column if not exists available_at timestamptz not null default now();
alter table dpq.tickets add column if not exists lease uuid;
create or replace function public.dpq_claim_support() returns jsonb
language plpgsql security definer set search_path='' as $$
declare ticket dpq.tickets%rowtype; token uuid:=gen_random_uuid();
begin
 select * into ticket from dpq.tickets where mail_status<>'sent' and available_at<=clock_timestamp() and attempts<10
 order by created_at for update skip locked limit 1;
 if not found then return null; end if;
 update dpq.tickets set lease=token,attempts=attempts+1,available_at=clock_timestamp()+interval '5 minutes' where id=ticket.id;
 return to_jsonb(ticket)||jsonb_build_object('lease',token);
end $$;
create or replace function public.dpq_finish_support(p_ticket uuid,p_lease uuid,p_sent boolean) returns boolean
language plpgsql security definer set search_path='' as $$
begin
 update dpq.tickets set mail_status=case when p_sent then 'sent' else 'failed' end,
 available_at=clock_timestamp()+interval '15 minutes',lease=null where id=p_ticket and lease=p_lease;
 return found;
end $$;
revoke all on function public.dpq_claim_support(),public.dpq_finish_support(uuid,uuid,boolean) from public,anon,authenticated;
grant execute on function public.dpq_claim_support(),public.dpq_finish_support(uuid,uuid,boolean) to service_role;
commit;
