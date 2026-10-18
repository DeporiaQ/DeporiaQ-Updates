// The real Edge handler under Node's TypeScript stripping; all HTTP is isolated.
import assert from 'node:assert/strict';
import {createHmac} from 'node:crypto';
let handler;
const env={SUPABASE_URL:'https://unit-project.supabase.co',SUPABASE_SERVICE_ROLE_KEY:'unit-service-secret',DPQ_IYZICO_ENVIRONMENT:'live',DPQ_IYZICO_API_KEY:'unit-api',DPQ_IYZICO_SECRET_KEY:'unit-key'};
globalThis.Deno={env:{get:key=>env[key]},serve:fn=>handler=fn};
await import('../../supabase/functions/payment-checkout/index.ts');
const order={id:'aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa',company_id:'company-a',actor:'owner-a',offer:'monthly',plan:'duo',months:1,amount_minor:12345,currency:'TRY',environment:'live',expires_at:'2050-01-01T00:00:00Z',provider_token:'unit-provider-token',payment_url:'https://payment.iyzipay.com/pay',paid:false};
const approved={status:'success',paymentStatus:'SUCCESS',fraudStatus:1,basketId:order.id,conversationId:order.id,currency:'TRY',price:'123.45',paidPrice:'123.45',paymentId:'12345',itemTransactions:[{itemId:'monthly',price:'123.45',transactionStatus:1,paymentTransactionId:'111'}]};
let calls=[],provider=approved,current={...order};
globalThis.fetch=async(url,options={})=>{
 const parsed=new URL(url);const body=JSON.parse(options.body||'{}');calls.push([parsed.pathname,body]);
 if(parsed.hostname==='unit-project.supabase.co') {
  if(parsed.pathname==='/auth/v1/user')return Response.json({id:'owner-a',email:'owner@example.invalid',email_confirmed_at:'2026-10-01T00:00:00Z'});
  assert.equal(options.headers.apikey,'unit-service-secret');
  const name=parsed.pathname.split('/').at(-1);
  const replies={dpq_checkout_get:current,dpq_checkout_by_token:current,dpq_checkout_by_payment:current,dpq_checkout_create:current,dpq_checkout_claim:true,dpq_checkout_poll_claim:true,dpq_checkout_confirm:{applied:true,valid_until:'2027-01-01T00:00:00Z'},dpq_checkout_observe:null,dpq_checkout_attach:null};
  assert(name in replies,'Unexpected RPC '+name);return Response.json(replies[name]);
 }
 assert.equal(parsed.origin,'https://api.iyzipay.com','No unmocked external destination');
 if(parsed.pathname.endsWith('/initialize/auth/ecom'))return Response.json({status:'success',token:'unit-provider-token',paymentPageUrl:'https://payment.iyzipay.com/pay'});
 return Response.json(provider);
};
async function request(action,body,headers={}) {
 const suffix=action?'?action='+action:'';
 return handler(new Request(env.SUPABASE_URL+'/functions/v1/payment-checkout'+suffix,{method:'POST',headers:{'Content-Type':'application/json',...headers},body:typeof body==='string'?body:JSON.stringify(body)}));
}
const finalized=()=>calls.filter(([path])=>path.endsWith('/dpq_checkout_confirm'));
assert.equal((await request('',{action:'create'})).status,401);assert.equal(calls.length,0);
assert.equal((await request('webhook',{...order})).status,401);assert.equal(calls.length,0);
let result=await request('callback','token='+order.provider_token,{'Content-Type':'application/x-www-form-urlencoded'});
assert.equal(result.status,200);assert.equal(finalized().length,1);assert((await result.text()).includes('doğrulandı'));
calls=[];provider={...approved,paidPrice:'0.01'};result=await request('callback','token='+order.provider_token);assert.equal(result.status,400);assert.equal(finalized().length,0);
calls=[];provider={...approved,fraudStatus:0};result=await request('fraud',{paymentId:12345,fraudStatus:1});assert.equal(result.status,503);assert.equal(finalized().length,0);assert(calls.some(([path])=>path.endsWith('/dpq_checkout_observe')));
calls=[];provider={...approved,fraudStatus:2};result=await request('fraud',{paymentId:12345,fraudStatus:-1});assert.equal(result.status,200);assert.equal(finalized().length,1,'Only provider lookup can approve, not posted fraud status');
calls=[];const notice={iyziEventType:'CHECKOUT_FORM_AUTH',iyziPaymentId:12345,token:order.provider_token,paymentConversationId:order.id,status:'SUCCESS'};
const signature=createHmac('sha256',env.DPQ_IYZICO_SECRET_KEY).update(env.DPQ_IYZICO_SECRET_KEY+notice.iyziEventType+notice.iyziPaymentId+notice.token+notice.paymentConversationId+notice.status).digest('hex');
result=await request('webhook',notice,{'x-iyz-signature-v3':signature});assert.equal(result.status,200);assert.equal(finalized().length,1);
calls=[];current={...order,paid:true};result=await request('webhook',notice,{'x-iyz-signature-v3':signature});assert.equal(result.status,200);assert.equal(finalized().length,0);
calls=[];current={...order,provider_token:null};const payload={action:'create',offer:'monthly',request_id:'bbbbbbbb-bbbb-4bbb-8bbb-bbbbbbbbbbbb',accepted_terms:true,amount_minor:1,buyer:{name:'Test',surname:'Buyer',email:'forged@example.invalid',identityNumber:'11111111110',gsmNumber:'+905551234567',address:'Test Street',city:'Izmir',country:'Turkey'}};
result=await request('',payload,{Authorization:'Bearer unit-user','x-forwarded-for':'127.0.0.1'});assert.equal(result.status,200);
const initialize=calls.find(([path])=>path.endsWith('/initialize/auth/ecom'))[1];assert.equal(initialize.price,'123.45');assert.equal(initialize.buyer.email,'owner@example.invalid');assert.equal(initialize.basketId,order.id);
assert.equal((await request('',{...payload,accepted_terms:false},{Authorization:'Bearer unit-user'})).status,400);
console.log('PASS actual Edge handler: auth, forged webhook, amount tamper, delayed approval, callback retry, server prices and verified buyer identity');
