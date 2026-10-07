-- Isolated contract fixture reconstructed from shipped migrations/client fields.
-- NOT a production migration. Live schema comparison remains mandatory.
create role anon; create role authenticated; create role service_role;
create schema auth;
create function auth.uid() returns uuid language sql stable as $$ select nullif(current_setting('request.jwt.claim.sub',true),'')::uuid $$;
grant usage on schema auth to authenticated;
grant execute on function auth.uid() to authenticated;
create table public.companies(id uuid primary key default gen_random_uuid(),name text);
create table public.company_members(company_id uuid references companies(id),user_id uuid,role text,active boolean,created_at timestamptz default now());
create table public.company_subscriptions(company_id uuid primary key references companies(id),status text,valid_until timestamptz,grace_until timestamptz,plan_code text,updated_at timestamptz default now());
create table public.locations(id uuid primary key default gen_random_uuid(),company_id uuid references companies(id),name text,location_type text,active boolean,unique(company_id,name));
create table public.products(id uuid primary key default gen_random_uuid(),company_id uuid references companies(id),barcode text,name text,sale_price numeric,purchase_price numeric,critical_stock numeric,active boolean,unique(company_id,barcode));
create table public.inventory(company_id uuid references companies(id),product_id uuid references products(id),location_id uuid references locations(id),quantity numeric not null check(quantity>=0),updated_at timestamptz default now(),unique(company_id,location_id,product_id));
create table public.cloud_devices(id uuid primary key default gen_random_uuid(),company_id uuid,device_code text,active boolean);
