"""Read-only compatibility gates; never log or export production metadata."""
import os,json,urllib.request,urllib.parse
base=os.environ['SUPABASE_URL'].rstrip('/')
host=urllib.parse.urlparse(base).hostname or ''
if not host.endswith('.supabase.co'):raise SystemExit('Invalid project URL')
ref=host.split('.')[0]
def management(path,body=None):
    req=urllib.request.Request('https://api.supabase.com/v1/projects/'+ref+path,
        data=None if body is None else json.dumps(body).encode(),
        headers={'Authorization':'Bearer '+os.environ['SUPABASE_ACCESS_TOKEN'],'Content-Type':'application/json'})
    try:
        with urllib.request.urlopen(req,timeout=25) as response:return json.load(response)
    except Exception:raise SystemExit('Compatibility check unavailable; no server changes were made.')
# The database returns a single Boolean. No schema definitions or customer rows
# leave the database, and no report/artifact is uploaded to the repository.
result=management('/database/query',{'query':"""
with required(table_schema,table_name,column_name) as (values
 ('public','companies','id'),('public','companies','name'),
 ('public','company_members','company_id'),('public','company_members','user_id'),
 ('public','company_members','role'),('public','company_members','active'),
 ('public','locations','id'),('public','locations','company_id'),('public','locations','name'),
 ('public','locations','location_type'),('public','locations','active'),
 ('public','company_subscriptions','company_id'),('public','company_subscriptions','status'),
 ('public','company_subscriptions','plan_code'),('public','company_subscriptions','valid_until'),
 ('auth','users','id'),('auth','users','email'),('auth','users','email_confirmed_at'))
select not exists(select 1 from required r where not exists(
 select 1 from information_schema.columns c where c.table_schema=r.table_schema and c.table_name=r.table_name and c.column_name=r.column_name))
 and not exists(select 1 from information_schema.columns c where c.table_schema='public'
 and c.table_name in ('companies','company_members','locations') and c.is_nullable='NO'
 and c.column_default is null and c.is_identity='NO' and c.is_generated='NEVER'
 and not exists(select 1 from required r where r.table_schema=c.table_schema and r.table_name=c.table_name and r.column_name=c.column_name))
 as compatible;
"""})
if not result or result[0].get('compatible') is not True:raise SystemExit('Schema compatibility gate failed; no server changes were made.')
print('PASS: enrollment schema compatibility gate')
# Configuration stays in memory. Print neither SMTP values nor tokens.
auth=management('/config/auth')
ready=bool(not auth.get('disable_signup') and auth.get('external_email_enabled')
    and not auth.get('mailer_autoconfirm') and auth.get('smtp_host') and auth.get('smtp_pass')
    and '{{ .Token }}' in str(auth.get('mailer_templates_confirmation_content','')))
print('PASS: email registration readiness gate' if ready else 'PENDING: email registration configuration required')
