// One-time operator setup. No credentials or customer metadata are logged.
// Requires the project's authorized Supabase Management token in Actions secrets.
import fs from 'node:fs';
const phase=process.argv[2]||'migrate';
if(!['migrate','email','enrollment'].includes(phase))throw new Error('Unknown setup phase');
const base=new URL(process.env.SUPABASE_URL||'');
if(base.protocol!=='https:'||!base.hostname.endsWith('.supabase.co'))throw new Error('Invalid project URL');
const token=process.env.SUPABASE_ACCESS_TOKEN;
if(!token)throw new Error('SUPABASE_ACCESS_TOKEN is required in Actions secrets');
async function management(path,body,method=body?'POST':'GET') {
 const response=await fetch('https://api.supabase.com/v1/projects/'+base.hostname.split('.')[0]+path,{method,signal:AbortSignal.timeout(45000),headers:{Authorization:'Bearer '+token,'Content-Type':'application/json'},body:body?JSON.stringify(body):undefined});
 if(!response.ok)throw new Error('Management access failed (HTTP '+response.status+'). No response body or secret is logged.');
 return response.json();
}
async function sql(query,read_only=false){return management('/database/query',{query,read_only});}
if(phase==='migrate') {
 const script=fs.readFileSync('server/012_onboarding_billing.sql','utf8').replace(/^begin;\s*$/mi,'').replace(/^commit;\s*$/mi,'');
 await sql(`begin; set local lock_timeout='10s'; set local statement_timeout='40s';
 lock table public.company_subscriptions in share mode;
 create temporary table dpq_expiry_checkpoint on commit drop as select company_id,status,valid_until,plan_code from public.company_subscriptions;
 ${script}
 do $$begin
 if exists((select company_id,status,valid_until,plan_code from public.company_subscriptions except select * from dpq_expiry_checkpoint)
 union all (select * from dpq_expiry_checkpoint except select company_id,status,valid_until,plan_code from public.company_subscriptions))
 then raise exception 'Existing subscription changed; migration rolled back';end if;
 end $$;
 commit;`);
 const ready=await sql('select public.dpq_0270_ready() as version',true);
 if(ready[0]?.version!=='0.27.0')throw new Error('Migration readiness check failed');
 console.log('PASS migration committed; existing subscription dates/status/plans unchanged. Registration and payment configuration remain separate.');
}
if(phase==='email') {
 const old=await management('/config/auth');
 const patch={mailer_autoconfirm:false,external_email_enabled:true,disable_signup:false,
   password_min_length:Math.max(14,Number(old.password_min_length)||0),
   mailer_templates_confirmation_content:'<h2>DeporiaQ</h2><p>E-posta doğrulama kodunuz / Your verification code:</p><p style="font-size:28px;font-weight:bold;letter-spacing:4px">{{ .Token }}</p><p>Bu kodu DeporiaQ kayıt ekranına yazın. Kodu kimseyle paylaşmayın.</p><p>Enter this code in DeporiaQ. Do not share it. If you did not request this email, ignore it.</p>',
   mailer_subjects_confirmation:'DeporiaQ e-posta doğrulama / Email verification'};
 if(!old.smtp_host||!old.smtp_pass) {
   const password=(process.env.DPQ_SMTP_PASSWORD||'').replaceAll(' ','');
   if(!password)throw new Error('Custom SMTP must be configured before public registration');
   Object.assign(patch,{smtp_host:'smtp.gmail.com',smtp_port:'465',smtp_user:'deporiaq@gmail.com',smtp_pass:password,smtp_admin_email:'deporiaq@gmail.com',smtp_sender_name:'DeporiaQ'});
 }
 // Keep existing MFA, sessions, CAPTCHA, rate limits and token-rotation settings.
 await management('/config/auth',patch,'PATCH');
 console.log('PASS email code configuration saved. Confirm delivery before opening registration. No email was sent by this script.');
}
if(phase==='enrollment') {
 if(process.env.DPQ_REGISTRATION_EMAIL_TESTED!=='true')throw new Error('Confirm an actual registration-code delivery before enabling enrollment');
 const auth=await management('/config/auth');
 if(auth.security_captcha_enabled)throw new Error('CAPTCHA is enabled: finish the desktop CAPTCHA flow before opening public registration; do not disable CAPTCHA');
 if(auth.disable_signup||!auth.external_email_enabled||auth.mailer_autoconfirm||!auth.smtp_host||!auth.smtp_pass||!String(auth.mailer_templates_confirmation_content).includes('{{ .Token }}'))throw new Error('Email registration gates are incomplete');
 // No plan price, checkout flag, current user or subscription is changed here.
 await sql('update dpq.commercial_config set enrollment_enabled=true where id=true');
 console.log('PASS self-service enrollment enabled. Live checkout remains separately controlled.');
}
