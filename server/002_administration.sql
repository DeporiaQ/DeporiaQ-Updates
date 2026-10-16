begin;
create table if not exists dpq.trial_claims (
 subject_hash text primary key, company_id uuid unique not null references public.companies(id),
 started_at timestamptz not null default now(), expires_at timestamptz not null default(now()+interval '30 days')
);
-- Called ONLY by the trusted enrollment service after identity/device checks.
-- Hash must be derived by the service, never accepted from a desktop payload.
create or replace function public.dpq_start_trial(p_company uuid,p_subject_hash text)
returns timestamptz language plpgsql security definer set search_path='' as $$
declare ending timestamptz;
begin
 if length(p_subject_hash)<32 then raise exception 'Verified enrollment identity required'; end if;
 insert into dpq.settings(company_id) values(p_company) on conflict do nothing;
 perform 1 from dpq.settings where company_id=p_company for update;
 if exists(select 1 from public.company_subscriptions where company_id=p_company) then raise exception 'Existing subscription must not be reset'; end if;
 insert into dpq.trial_claims(subject_hash,company_id) values(p_subject_hash,p_company) returning expires_at into ending;
 insert into public.company_subscriptions(company_id,status,valid_until,plan_code) values(p_company,'trial',ending,'demo');
 return ending;
end $$;
-- Enabling is deliberately a separate operation after inventory reconciliation.
create or replace function public.dpq_enable(p_company uuid,p_plan text,p_center uuid)
returns void language plpgsql security definer set search_path='' as $$
begin
 if not exists(select 1 from dpq.plans where code=p_plan) then raise exception 'Unknown plan'; end if;
 if not exists(select 1 from public.locations where id=p_center and company_id=p_company and active) then raise exception 'Invalid center'; end if;
 if not exists(select 1 from public.company_subscriptions where company_id=p_company) then raise exception 'Subscription missing'; end if;
 insert into dpq.settings(company_id) values(p_company) on conflict do nothing;
 perform 1 from dpq.settings where company_id=p_company for update;
 if exists(select 1 from dpq.settings where company_id=p_company and enabled) then raise exception 'Already enabled: use billing/admin plan change'; end if;
 update public.company_subscriptions set plan_code=p_plan,updated_at=clock_timestamp() where company_id=p_company;
 update dpq.settings set enabled=true,center_id=p_center where company_id=p_company;
end $$;
-- Trusted verified-payment adapter only. Exact match to server-created checkout.
create or replace function public.dpq_apply_payment(p_event text,p_order uuid,p_amount bigint,p_currency text)
returns jsonb language plpgsql security definer set search_path='' as $$
declare checkout dpq.checkout_orders%rowtype; previous dpq.payments%rowtype;
begin
 select * into checkout from dpq.checkout_orders where id=p_order;
 if not found then raise exception 'Unknown checkout'; end if;
 perform 1 from dpq.settings where company_id=checkout.company_id for update;
 select * into checkout from dpq.checkout_orders where id=p_order for update;
 if p_event is null or length(p_event) not between 1 and 200 or p_amount is distinct from checkout.amount_minor or p_currency is distinct from checkout.currency then raise exception 'Payment mismatch'; end if;
 select * into previous from dpq.payments where provider_event=p_event;
 if found then
 if previous.order_id<>p_order::text then raise exception 'Event replay mismatch'; end if;
 return '{"applied":true,"duplicate":true}';
 end if;
 if checkout.paid then return '{"applied":true,"duplicate":true}'; end if;
 if checkout.period_end<=clock_timestamp() then raise exception 'Stale checkout requires reconciliation'; end if;
 insert into dpq.payments(provider_event,company_id,order_id,amount_minor,currency,plan,period_end)
 values(p_event,checkout.company_id,p_order::text,p_amount,p_currency,checkout.plan,checkout.period_end);
 update dpq.checkout_orders set paid=true where id=p_order;
 -- Never shorten paid entitlement. Suspended accounts require staff review.
 if exists(select 1 from public.company_subscriptions where company_id=checkout.company_id and status='suspended') then raise exception 'Suspended account: manual reconciliation required'; end if;
 update public.company_subscriptions set status='active',plan_code=checkout.plan,
 valid_until=greatest(valid_until,checkout.period_end),updated_at=clock_timestamp() where company_id=checkout.company_id;
 if not found then raise exception 'Subscription missing'; end if;
 return '{"applied":true,"duplicate":false}';
end $$;
revoke all on table dpq.trial_claims from public,anon,authenticated;
revoke all on function public.dpq_start_trial(uuid,text),public.dpq_enable(uuid,text,uuid),public.dpq_apply_payment(text,uuid,bigint,text) from public,anon,authenticated;
grant execute on function public.dpq_start_trial(uuid,text),public.dpq_enable(uuid,text,uuid),public.dpq_apply_payment(text,uuid,bigint,text) to service_role;
commit;
