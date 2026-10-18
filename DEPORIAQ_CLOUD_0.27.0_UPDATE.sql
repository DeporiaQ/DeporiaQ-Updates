-- 0.27: self-service enrollment and server-priced checkout. Existing expiry dates
-- are never changed by installation. Live checkout stays off until configured.
begin;
create table if not exists dpq.commercial_config (
 id boolean primary key default true check(id), enrollment_enabled boolean not null default false,
 checkout_enabled boolean not null default false, environment text not null default 'sandbox' check(environment in ('sandbox','live')),
 terms_url text not null default '', privacy_url text not null default ''
);
insert into dpq.commercial_config(id) values(true) on conflict do nothing;
create table if not exists dpq.offers (
 code text primary key, plan text not null references dpq.plans(code),
 months integer not null check(months between 1 and 12),
 amount_minor bigint not null check(amount_minor between 100 and 100000000),
 currency text not null default 'TRY' check(currency='TRY'), active boolean not null default false,
 updated_at timestamptz not null default now(), check(plan<>'demo')
);
create table if not exists dpq.enrollments (
 user_id uuid primary key, company_id uuid unique not null references public.companies(id),
 created_at timestamptz not null default now()
);
alter table dpq.checkout_orders add column if not exists request_id uuid;
alter table dpq.checkout_orders add column if not exists actor uuid;
alter table dpq.checkout_orders add column if not exists offer text references dpq.offers(code);
alter table dpq.checkout_orders add column if not exists months integer;
alter table dpq.checkout_orders add column if not exists created_at timestamptz not null default now();
alter table dpq.checkout_orders add column if not exists expires_at timestamptz;
alter table dpq.checkout_orders add column if not exists environment text;
alter table dpq.checkout_orders add column if not exists provider_token text;
alter table dpq.checkout_orders add column if not exists payment_url text;
alter table dpq.checkout_orders add column if not exists payment_state text not null default 'created';
alter table dpq.checkout_orders add column if not exists provider_transaction text;
alter table dpq.checkout_orders add column if not exists provider_payment_id text;
alter table dpq.checkout_orders add column if not exists last_checked_at timestamptz;
create unique index if not exists dpq_checkout_request on dpq.checkout_orders(actor,request_id);
create unique index if not exists dpq_checkout_token on dpq.checkout_orders(provider_token) where provider_token is not null;
create unique index if not exists dpq_checkout_provider_payment on dpq.checkout_orders(environment,provider_payment_id) where provider_payment_id is not null;
revoke all on dpq.commercial_config,dpq.offers,dpq.enrollments from public,anon,authenticated;
alter table dpq.commercial_config enable row level security;
alter table dpq.offers enable row level security;
alter table dpq.enrollments enable row level security;

create or replace function public.dpq_enroll(p_name text)
returns jsonb language plpgsql security definer set search_path='' as $$
declare u uuid:=auth.uid(); c uuid; center uuid; email text; ending timestamptz; n text:=btrim(p_name);
begin
 if u is null then raise exception 'DPQ_AUTH';end if;
 perform pg_advisory_xact_lock(hashtextextended(u::text,270));
 select lower(btrim(a.email)) into email from auth.users a where a.id=u and a.email_confirmed_at is not null;
 if email is null or email='' then raise exception 'DPQ_EMAIL_VERIFY: Confirm your email first';end if;
 select company_id into c from dpq.enrollments where user_id=u;
 if c is not null then
  if not exists(select 1 from public.company_members where user_id=u and company_id=c and active) then raise exception 'DPQ_MEMBERSHIP';end if;
  return jsonb_build_object('company_id',c,'created',false);
 end if;
 -- Inactive memberships must not be bypassed by creating a second company.
 if exists(select 1 from public.company_members where user_id=u) then raise exception 'DPQ_ALREADY_MEMBER';end if;
 if not exists(select 1 from dpq.commercial_config where id and enrollment_enabled) then raise exception 'DPQ_SIGNUP_CLOSED';end if;
 if n is null or char_length(n) not between 2 and 120 or n ~ '[[:cntrl:]]' then raise exception 'DPQ_INPUT';end if;
 insert into public.companies(name,created_by) values(n,u) returning id into c;
 insert into public.company_members(company_id,user_id,role,active) values(c,u,'owner',true);
 insert into public.locations(company_id,name,location_type,active) values(c,'Merkez Depo','center',true) returning id into center;
 -- Identity comes from auth.users, never a client-supplied hash or user id.
 ending:=public.dpq_start_trial(c,encode(sha256(convert_to('email:'||email,'UTF8')),'hex'));
 perform public.dpq_enable(c,'demo',center);
 insert into dpq.enrollments(user_id,company_id) values(u,c);
 insert into dpq.audit(company_id,actor,action,payload) values(c,u,'self_enrollment',jsonb_build_object('trial_until',ending));
 return jsonb_build_object('company_id',c,'created',true,'valid_until',ending);
end $$;
revoke all on function public.dpq_enroll(text) from public,anon;
grant execute on function public.dpq_enroll(text) to authenticated;

create or replace function public.dpq_checkout_catalog()
returns jsonb language plpgsql security definer set search_path='' as $$
declare u uuid:=auth.uid(); conf dpq.commercial_config%rowtype; owner boolean;
begin
 if u is null then raise exception 'DPQ_AUTH';end if;
 select * into conf from dpq.commercial_config where id;
 owner:=(select count(*)=1 and bool_and(role='owner') from public.company_members where user_id=u and active);
 return jsonb_build_object('enabled',conf.checkout_enabled,'environment',conf.environment,'can_buy',coalesce(owner,false),
 'terms_url',conf.terms_url,'privacy_url',conf.privacy_url,'offers',coalesce((select jsonb_agg(jsonb_build_object(
 'code',o.code,'plan',o.plan,'devices',p.devices,'months',o.months,'amount_minor',o.amount_minor,'currency',o.currency) order by p.devices,o.months)
 from dpq.offers o join dpq.plans p on p.code=o.plan where o.active and conf.checkout_enabled),'[]'));
end $$;
revoke all on function public.dpq_checkout_catalog() from public,anon;
grant execute on function public.dpq_checkout_catalog() to authenticated;

create or replace function public.dpq_checkout_create(p_user uuid,p_offer text,p_request uuid)
returns jsonb language plpgsql security definer set search_path='' as $$
declare c uuid; role_name text; o dpq.offers%rowtype; conf dpq.commercial_config%rowtype; ord dpq.checkout_orders%rowtype; sub public.company_subscriptions%rowtype;
begin
 if p_user is null or p_request is null or (select count(*) from public.company_members where user_id=p_user and active)<>1 then raise exception 'DPQ_AUTH';end if;
 select company_id,role into c,role_name from public.company_members where user_id=p_user and active;
 if role_name<>'owner' then raise exception 'DPQ_OWNER';end if;
 perform 1 from dpq.settings where company_id=c for update;
 if not found then raise exception 'DPQ_NOT_READY';end if;
 select * into ord from dpq.checkout_orders where actor=p_user and request_id=p_request;
 if found then
  if ord.offer is distinct from p_offer then raise exception 'DPQ_REQUEST_CONFLICT';end if;
  return to_jsonb(ord);
 end if;
 select * into conf from dpq.commercial_config where id;
 if not conf.checkout_enabled or conf.terms_url!~'^https://' or conf.privacy_url!~'^https://' then raise exception 'DPQ_BILLING_CLOSED';end if;
 select * into o from dpq.offers where code=p_offer and active;
 if not found then raise exception 'DPQ_OFFER';end if;
 select * into sub from public.company_subscriptions where company_id=c for update;
 if not found or sub.status='suspended' then raise exception 'DPQ_SUBSCRIPTION_REVIEW';end if;
 if (select devices from dpq.plans where code=o.plan)<(select count(*) from dpq.devices where company_id=c and active) then raise exception 'DPQ_LIMIT';end if;
 -- No paid-plan downgrade can silently remove an existing entitlement.
 if sub.status='active' and sub.valid_until>clock_timestamp() and (select devices from dpq.plans where code=o.plan)<(select devices from dpq.plans where code=sub.plan_code) then raise exception 'DPQ_DOWNGRADE';end if;
 if (select count(*) from dpq.checkout_orders where company_id=c and created_at>clock_timestamp()-interval '1 hour')>=10 then raise exception 'DPQ_BILLING_RATE';end if;
 insert into dpq.checkout_orders(company_id,plan,amount_minor,currency,period_end,actor,request_id,offer,months,expires_at,environment)
 values(c,o.plan,o.amount_minor,o.currency,greatest(clock_timestamp(),sub.valid_until)+make_interval(months=>o.months),p_user,p_request,o.code,o.months,clock_timestamp()+interval '30 minutes',conf.environment)
 returning * into ord;
 return to_jsonb(ord);
end $$;

create or replace function public.dpq_checkout_attach(p_order uuid,p_token text,p_url text)
returns void language plpgsql security definer set search_path='' as $$
declare ord dpq.checkout_orders%rowtype;
begin
 select * into ord from dpq.checkout_orders where id=p_order for update;
 if not found or ord.expires_at<clock_timestamp() or char_length(p_token) not between 10 and 200 then raise exception 'DPQ_CHECKOUT';end if;
 if ord.provider_token is not null and ord.provider_token<>p_token then raise exception 'DPQ_REQUEST_CONFLICT';end if;
 if (ord.environment='live' and p_url!~'^https://(payment\.iyzipay\.com|checkout\.iyzipay\.com)/') or
 (ord.environment='sandbox' and p_url!~'^https://(sandbox-payment\.iyzipay\.com|sandbox-checkout\.iyzipay\.com)/') then raise exception 'DPQ_PAYMENT_URL';end if;
 update dpq.checkout_orders set provider_token=p_token,payment_url=p_url,payment_state='pending' where id=p_order;
end $$;

-- Claim before contacting the provider. An interrupted initialize is reviewed,
-- never blindly retried (a second hosted page could collect a second payment).
create or replace function public.dpq_checkout_claim(p_order uuid)
returns boolean language plpgsql security definer set search_path='' as $$
begin
 update dpq.checkout_orders set payment_state='initializing' where id=p_order and payment_state='created' and expires_at>clock_timestamp();
 return found;
end $$;
create or replace function public.dpq_checkout_poll_claim(p_order uuid)
returns boolean language plpgsql security definer set search_path='' as $$
begin
 update dpq.checkout_orders set last_checked_at=clock_timestamp() where id=p_order and (last_checked_at is null or last_checked_at<clock_timestamp()-interval '5 seconds');
 return found;
end $$;

-- Only a verified provider result can reach this service-role-only function.
create or replace function public.dpq_checkout_confirm(p_order uuid,p_token text,p_event text,p_amount bigint,p_currency text,p_transaction text)
returns jsonb language plpgsql security definer set search_path='' as $$
declare ord dpq.checkout_orders%rowtype; sub public.company_subscriptions%rowtype; ending timestamptz; previous dpq.payments%rowtype;
begin
 select * into ord from dpq.checkout_orders where id=p_order;
 if not found then raise exception 'DPQ_CHECKOUT';end if;
 perform 1 from dpq.settings where company_id=ord.company_id for update;
 select * into ord from dpq.checkout_orders where id=p_order for update;
 if p_token is null or p_token is distinct from ord.provider_token or p_amount is distinct from ord.amount_minor or p_currency is distinct from ord.currency
 or p_event is null or char_length(p_event) not between 1 and 200 or coalesce(p_transaction,'')='' then raise exception 'DPQ_PAYMENT_MISMATCH';end if;
 select * into previous from dpq.payments where provider_event=p_event;
 if found then
  if previous.order_id<>p_order::text then raise exception 'DPQ_REPLAY';end if;
  return jsonb_build_object('applied',true,'duplicate',true,'valid_until',previous.period_end);
 end if;
 if ord.paid then raise exception 'DPQ_PAYMENT_ALREADY_PAID';end if;
 -- A sandbox result never grants live entitlement.
 if ord.environment<>'live' then
  update dpq.checkout_orders set payment_state='sandbox_paid',last_checked_at=clock_timestamp(),provider_transaction=p_transaction where id=p_order;
  return '{"applied":false,"sandbox":true}';
 end if;
 select * into sub from public.company_subscriptions where company_id=ord.company_id for update;
 if not found or sub.status='suspended' then raise exception 'DPQ_SUBSCRIPTION_REVIEW';end if;
 if sub.status='active' and sub.valid_until>clock_timestamp() and (select devices from dpq.plans where code=ord.plan)<(select devices from dpq.plans where code=sub.plan_code) then raise exception 'DPQ_DOWNGRADE_REVIEW';end if;
 ending:=greatest(clock_timestamp(),sub.valid_until)+make_interval(months=>ord.months);
 insert into dpq.payments(provider_event,company_id,order_id,amount_minor,currency,plan,period_end)
 values(p_event,ord.company_id,p_order::text,p_amount,p_currency,ord.plan,ending);
 update public.company_subscriptions set status='active',plan_code=ord.plan,valid_until=ending,updated_at=clock_timestamp() where company_id=ord.company_id;
 update dpq.checkout_orders set paid=true,period_end=ending,payment_state='paid',provider_transaction=p_transaction,last_checked_at=clock_timestamp() where id=p_order;
 insert into dpq.audit(company_id,actor,action,payload) values(ord.company_id,ord.actor,'subscription_payment',jsonb_build_object('order',p_order,'plan',ord.plan,'valid_until',ending));
 return jsonb_build_object('applied',true,'duplicate',false,'valid_until',ending);
end $$;

create or replace function public.dpq_checkout_get(p_user uuid,p_order uuid)
returns jsonb language plpgsql security definer set search_path='' as $$
begin
 if not exists(select 1 from dpq.checkout_orders o join public.company_members m on m.company_id=o.company_id where o.id=p_order and m.user_id=p_user and m.active and m.role='owner') then raise exception 'DPQ_OWNER';end if;
 return(select to_jsonb(o) from dpq.checkout_orders o where id=p_order);
end $$;
create or replace function public.dpq_checkout_by_token(p_token text)
returns jsonb language sql security definer set search_path='' as $$ select to_jsonb(o) from dpq.checkout_orders o where provider_token=p_token $$;
-- Payment IDs come only from a server-verified provider response. IFN merely
-- triggers another provider lookup; its posted fraudStatus is never trusted.
create or replace function public.dpq_checkout_observe(p_order uuid,p_token text,p_payment text)
returns void language plpgsql security definer set search_path='' as $$
begin
 if p_payment is null or p_payment!~'^[0-9]{1,40}$' then raise exception 'DPQ_PAYMENT_MISMATCH';end if;
 update dpq.checkout_orders set provider_payment_id=p_payment where id=p_order and provider_token=p_token
 and (provider_payment_id is null or provider_payment_id=p_payment);
 if not found then raise exception 'DPQ_PAYMENT_MISMATCH';end if;
end $$;
create or replace function public.dpq_checkout_by_payment(p_payment text,p_environment text)
returns jsonb language sql security definer set search_path='' as $$
 select to_jsonb(o) from dpq.checkout_orders o where provider_payment_id=p_payment and environment=p_environment
$$;
revoke all on function public.dpq_checkout_observe(uuid,text,text),public.dpq_checkout_by_payment(text,text) from public,anon,authenticated;
grant execute on function public.dpq_checkout_observe(uuid,text,text),public.dpq_checkout_by_payment(text,text) to service_role;
revoke all on function public.dpq_checkout_create(uuid,text,uuid),public.dpq_checkout_attach(uuid,text,text),public.dpq_checkout_confirm(uuid,text,text,bigint,text,text),public.dpq_checkout_get(uuid,uuid),public.dpq_checkout_by_token(text),public.dpq_checkout_claim(uuid),public.dpq_checkout_poll_claim(uuid) from public,anon,authenticated;
grant execute on function public.dpq_checkout_create(uuid,text,uuid),public.dpq_checkout_attach(uuid,text,text),public.dpq_checkout_confirm(uuid,text,text,bigint,text,text),public.dpq_checkout_get(uuid,uuid),public.dpq_checkout_by_token(text),public.dpq_checkout_claim(uuid),public.dpq_checkout_poll_claim(uuid) to service_role;
create or replace function public.dpq_0270_ready() returns text language sql set search_path='' as $$select '0.27.0'::text$$;
revoke all on function public.dpq_0270_ready() from public;
grant execute on function public.dpq_0270_ready() to anon,authenticated,service_role;
notify pgrst,'reload schema';
commit;

-- Old entry points must obey the same verified, one-company enrollment rules.
-- No customer records, subscription periods, Auth users or sessions are changed.
begin;
create or replace function public.create_company(company_name text)
returns uuid language sql security invoker set search_path='' as $$
 select (public.dpq_enroll(company_name)->>'company_id')::uuid
$$;
revoke all on function public.create_company(text) from public,anon;
grant execute on function public.create_company(text) to authenticated,service_role;

do $$ declare signature text; target regprocedure; begin
 foreach signature in array array[
  'public.apply_stock_movement(uuid,uuid,uuid,text,numeric,numeric,text,text)',
  'public.has_company_role(uuid,text[])','public.is_company_member(uuid)'
 ] loop
  target:=to_regprocedure(signature);
  if target is not null then
   execute format('revoke all on function %s from public,anon',target);
   execute format('grant execute on function %s to authenticated,service_role',target);
  end if;
 end loop;
 foreach signature in array array['public.handle_new_user()','public.rls_auto_enable()'] loop
  target:=to_regprocedure(signature);
  if target is not null then execute format('revoke all on function %s from public,anon,authenticated',target);end if;
 end loop;
 if to_regprocedure('public.set_updated_at()') is not null then
  alter function public.set_updated_at() set search_path='';
 end if;
end $$;

create index if not exists dpq_checkout_company_created on dpq.checkout_orders(company_id,created_at);
create index if not exists dpq_checkout_offer on dpq.checkout_orders(offer);
create index if not exists dpq_offers_plan on dpq.offers(plan);
notify pgrst,'reload schema';
commit;
