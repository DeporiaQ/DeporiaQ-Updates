// User authorization and SQL leases prevent cross-account delivery and replay.
// The recipient is fixed. No caller-controlled headers, address or SMTP settings.
import nodemailer from 'npm:nodemailer@7.0.12';
const url = Deno.env.get('SUPABASE_URL')!;
const anon = Deno.env.get('SUPABASE_ANON_KEY')!;
const service = Deno.env.get('SUPABASE_SERVICE_ROLE_KEY')!;
const transport = nodemailer.createTransport({
  host:'smtp.gmail.com',port:465,secure:true,
  auth:{user:'deporiaq@gmail.com',pass:Deno.env.get('DPQ_SMTP_PASSWORD')!},
  connectionTimeout:10000,greetingTimeout:10000,socketTimeout:20000,
});
async function rpc(name:string,body:unknown,token:string,key=anon) {
  const response=await fetch(`${url}/rest/v1/rpc/${name}`,{method:'POST',headers:{apikey:key,Authorization:`Bearer ${token}`,'Content-Type':'application/json'},body:JSON.stringify(body)});
  if(!response.ok) throw new Error(`RPC ${name}: ${response.status}`);
  return await response.json();
}
Deno.serve(async(req:Request)=>{
  if(req.method!=='POST')return Response.json({error:'POST required'},{status:405});
  const authorization=req.headers.get('Authorization')||'';
  if(!authorization.startsWith('Bearer '))return Response.json({error:'Authentication required'},{status:401});
  const token=authorization.slice(7);
  const auth=await fetch(`${url}/auth/v1/user`,{headers:{apikey:anon,Authorization:authorization}});
  if(!auth.ok)return Response.json({error:'Authentication required'},{status:401});
  let ticket:any;
  try {
    const body=await req.json();
    if(typeof body.ticket_id!=='string'||!/^[a-f0-9-]{36}$/i.test(body.ticket_id))return Response.json({error:'Invalid ticket'},{status:400});
    ticket=await rpc('dpq_claim_own_support',{p_ticket:body.ticket_id},token);
    if(!ticket)return Response.json({status:'queued_or_sent'});
    const info=await transport.sendMail({
      from:'deporiaq@gmail.com',to:'deporiaq@gmail.com',
      subject:`DeporiaQ destek talebi ${ticket.id}`,
      messageId:`<deporiaq-support-${ticket.id}@gmail.com>`,
      text:`Takip: ${ticket.id}\nŞirket: ${ticket.company_id}\nKonu: ${ticket.subject}\nİletişim: ${ticket.contact}\n\n${ticket.message}`,
    });
    if(!info.accepted?.includes('deporiaq@gmail.com'))throw new Error('Recipient not accepted');
    const finished=await rpc('dpq_finish_support',{p_ticket:ticket.id,p_lease:ticket.lease,p_sent:true},service,service);
    if(!finished)throw new Error('Lease acknowledgement failed');
    return Response.json({status:'sent'});
  } catch {
    if(ticket)try{await rpc('dpq_finish_support',{p_ticket:ticket.id,p_lease:ticket.lease,p_sent:false},service,service);}catch{}
    // Never return provider errors or credentials to the desktop application.
    return Response.json({status:'queued',message:'Gönderim yeniden denenecek.'},{status:503});
  }
});
