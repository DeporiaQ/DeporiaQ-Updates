"""Run on a trusted server/scheduler. NEVER bundle credentials or this job in EXE.
Required env: DPQ_SUPABASE_URL, DPQ_SERVICE_ROLE_KEY, DPQ_SMTP_HOST,
DPQ_SMTP_USER, DPQ_SMTP_PASSWORD, DPQ_MAIL_FROM. Optional DPQ_SMTP_PORT=465.
Uses SMTP over TLS. Recipient is fixed; client cannot turn this into a mail relay.
"""
import json
import os
import smtplib
import ssl
import urllib.request
from email.message import EmailMessage


def rpc(action,payload):
    key=os.environ['DPQ_SERVICE_ROLE_KEY']
    request=urllib.request.Request(os.environ['DPQ_SUPABASE_URL'].rstrip('/')+'/rest/v1/rpc/'+action,
      data=json.dumps(payload).encode(),headers={'Authorization':'Bearer '+key,'apikey':key,'Content-Type':'application/json'})
    with urllib.request.urlopen(request,timeout=20) as r:return json.load(r)


def deliver(ticket):
    msg=EmailMessage();msg['From']=os.environ['DPQ_MAIL_FROM'];msg['To']='deporiaq@gmail.com'
    # Do not put untrusted user text into headers.
    msg['Subject']='DeporiaQ destek talebi '+str(ticket['id'])
    msg['Message-ID']='<deporiaq-support-'+str(ticket['id'])+'@'+os.environ['DPQ_MAIL_FROM'].split('@')[-1]+'>'
    msg.set_content(f"Takip: {ticket['id']}\nŞirket: {ticket['company_id']}\nKonu: {ticket['subject']}\nİletişim: {ticket['contact']}\n\n{ticket['message']}")
    with smtplib.SMTP_SSL(os.environ['DPQ_SMTP_HOST'],int(os.getenv('DPQ_SMTP_PORT','465')),context=ssl.create_default_context(),timeout=30) as smtp:
        smtp.login(os.environ['DPQ_SMTP_USER'],os.environ['DPQ_SMTP_PASSWORD'])
        refused=smtp.send_message(msg)
        if refused:raise RuntimeError('SMTP recipient refused')


def run_once(rpc_fn=rpc,send_fn=deliver):
    ticket=rpc_fn('dpq_claim_support',{})
    if not ticket:return False
    try:send_fn(ticket)
    except Exception:
        rpc_fn('dpq_finish_support',{'p_ticket':ticket['id'],'p_lease':ticket['lease'],'p_sent':False})
        return False
    rpc_fn('dpq_finish_support',{'p_ticket':ticket['id'],'p_lease':ticket['lease'],'p_sent':True})
    return True

if __name__=='__main__':
    for _ in range(50):
        if not run_once():break
