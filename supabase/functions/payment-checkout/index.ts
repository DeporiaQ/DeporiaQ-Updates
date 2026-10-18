import {providerRequest,paymentURL,money,verifiedPayment,buyerPayload} from './provider.mjs';
const base=Deno.env.get('SUPABASE_URL')!;
const service=Deno.env.get('SUPABASE_SERVICE_ROLE_KEY')!;
const uuid=/^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i;
const headers={'Content-Type':'application/json','Cache-Control':'no-store','X-Content-Type-Options':'nosniff'};
const json=(body:unknown,status=200)=>new Response(JSON.stringify(body),{status,headers});
async function rpc(name:string,payload:unknown) {
  const r=await fetch(base+'/rest/v1/rpc/'+name,{method:'POST',signal:AbortSignal.timeout(12000),headers:{apikey:service,Authorization:'Bearer '+service,'Content-Type':'application/json'},body:JSON.stringify(payload)});
  const body=await r.json();if(!r.ok)throw new Error(String(body.message||'DPQ_SERVER'));return body;
}
function config(environment:string) {
  if(Deno.env.get('DPQ_IYZICO_ENVIRONMENT')!==environment)throw new Error('DPQ_BILLING_CLOSED');
  const apiKey=Deno.env.get('DPQ_IYZICO_API_KEY'),secret=Deno.env.get('DPQ_IYZICO_SECRET_KEY');
  if(!apiKey||!secret)throw new Error('DPQ_BILLING_CLOSED');return {environment,apiKey,secret};
}
async function authenticated(req:Request) {
  const token=req.headers.get('Authorization')||'';
  if(!token.startsWith('Bearer '))throw new Error('DPQ_AUTH');
  const r=await fetch(base+'/auth/v1/user',{headers:{apikey:service,Authorization:token},signal:AbortSignal.timeout(10000)});
  if(!r.ok)throw new Error('DPQ_AUTH');const user=await r.json();
  if(!user.id||!user.email||!user.email_confirmed_at)throw new Error('DPQ_AUTH');return user;
}
async function reconcile(order:any) {
  if(order.paid)return {paid:true,valid_until:order.period_end};
  if(order.payment_state==='sandbox_paid')return {paid:false,sandbox:true};
  if(!order.provider_token)return {paid:false,pending:true};
  if(!await rpc('dpq_checkout_poll_claim',{p_order:order.id}))return {paid:false,pending:true};
  const result=await providerRequest(config(order.environment),'/payment/iyzipos/checkoutform/auth/ecom/detail',{locale:'tr',conversationId:order.id,token:order.provider_token});
  const verified=verifiedPayment(result,order);
  if(!verified.event)return {paid:false,...verified};
  const applied=await rpc('dpq_checkout_confirm',{p_order:order.id,p_token:order.provider_token,p_event:verified.event,p_amount:order.amount_minor,p_currency:order.currency,p_transaction:verified.transaction});
  return {paid:applied.applied===true,sandbox:applied.sandbox===true,valid_until:applied.valid_until};
}
Deno.serve(async(req:Request)=>{
  if(req.method!=='POST')return json({error:'METHOD_NOT_ALLOWED'},405);
  try {
    if(Number(req.headers.get('content-length')||0)>8192)throw new Error('DPQ_INPUT');
    const text=await req.text();if(text.length>8192)throw new Error('DPQ_INPUT');
    if(new URL(req.url).searchParams.get('action')==='callback') {
      const token=new URLSearchParams(text).get('token')||'';
      if(token.length<10||token.length>200)throw new Error('DPQ_CHECKOUT');
      const order=await rpc('dpq_checkout_by_token',{p_token:token});if(!order)throw new Error('DPQ_CHECKOUT');
      const result=await reconcile(order);
      const message=result.paid?'Ödemeniz doğrulandı. DeporiaQ uygulamasına dönebilirsiniz.':result.sandbox?'Test ödemesi tamamlandı. Gerçek abonelik değiştirilmedi.':'Ödeme sonucu kontrol ediliyor. DeporiaQ içindeki Ödeme Durumunu Denetle düğmesini kullanın.';
      // Plain text works with the Supabase gateway's content-type restrictions.
      return new Response(message,{headers:{'Content-Type':'text/plain; charset=utf-8','Cache-Control':'no-store'}});
    }
    const user=await authenticated(req),payload=JSON.parse(text);
    if(payload.action==='status') {
      if(!uuid.test(payload.order_id||''))throw new Error('DPQ_INPUT');
      const order=await rpc('dpq_checkout_get',{p_user:user.id,p_order:payload.order_id});
      return json(await reconcile(order));
    }
    if(payload.action!=='create'||!uuid.test(payload.request_id||'')||payload.accepted_terms!==true)throw new Error('DPQ_INPUT');
    const forwarded=req.headers.get('x-forwarded-for')?.split(',')[0]?.trim()||'';
    if(!/^[\da-fA-F:.]{3,45}$/.test(forwarded))throw new Error('DPQ_NETWORK');
    const buyer=buyerPayload(payload.buyer,user,forwarded);
    const order=await rpc('dpq_checkout_create',{p_user:user.id,p_offer:payload.offer,p_request:payload.request_id});
    const settings=config(order.environment);
    if(order.paid)return json({order_id:order.id,paid:true});
    if(order.expires_at<=new Date().toISOString())throw new Error('DPQ_CHECKOUT_EXPIRED');
    if(order.provider_token)return json({order_id:order.id,url:paymentURL(order.payment_url,order.environment),environment:order.environment});
    if(!await rpc('dpq_checkout_claim',{p_order:order.id}))throw new Error('DPQ_CHECKOUT_REVIEW');
    const address={contactName:buyer.name+' '+buyer.surname,city:buyer.city,country:buyer.country,address:buyer.registrationAddress};
    const result=await providerRequest(settings,'/payment/iyzipos/checkoutform/initialize/auth/ecom',{
      locale:payload.locale==='en'?'en':'tr',conversationId:order.id,price:money(order.amount_minor),paidPrice:money(order.amount_minor),
      currency:order.currency,basketId:order.id,paymentGroup:'SUBSCRIPTION',enabledInstallments:[1],
      callbackUrl:base+'/functions/v1/payment-checkout?action=callback',buyer,billingAddress:address,
      basketItems:[{id:order.offer,name:'DeporiaQ '+order.plan+' / '+order.months+' ay',category1:'Software',itemType:'VIRTUAL',price:money(order.amount_minor)}]});
    if(result.status!=='success'||typeof result.token!=='string')throw new Error('DPQ_PROVIDER_UNAVAILABLE');
    const url=paymentURL(result.paymentPageUrl,order.environment);
    await rpc('dpq_checkout_attach',{p_order:order.id,p_token:result.token,p_url:url});
    return json({order_id:order.id,url,environment:order.environment});
  }catch(error) {
    // Never return provider replies, PII, tokens or server credentials.
    const code=String((error as Error).message).match(/DPQ_[A-Z_]+/)?.[0]||'DPQ_PAYMENT_UNAVAILABLE';
    return json({error:code},code==='DPQ_AUTH'?401:400);
  }
});
