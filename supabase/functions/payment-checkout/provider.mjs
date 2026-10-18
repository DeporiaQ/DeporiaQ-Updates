// Pure iyzico protocol helpers. Tested in Node; executed in the Edge runtime.
export function minorUnits(value) {
  const text=String(value);
  if(!/^\d{1,9}(\.\d{1,2})?$/.test(text))throw new Error('DPQ_PAYMENT_AMOUNT');
  const [whole,fraction='']=text.split('.');return Number(whole)*100+Number(fraction.padEnd(2,'0'));
}
export function money(minor) {
  if(!Number.isSafeInteger(minor)||minor<=0)throw new Error('DPQ_PAYMENT_AMOUNT');
  return `${Math.floor(minor/100)}.${String(minor%100).padStart(2,'0')}`;
}
export function paymentURL(value,environment) {
  const u=new URL(value);const hosts=environment==='live'?['payment.iyzipay.com','checkout.iyzipay.com']:['sandbox-payment.iyzipay.com','sandbox-checkout.iyzipay.com'];
  if(u.protocol!=='https:'||u.username||u.password||u.port||!hosts.includes(u.hostname))throw new Error('DPQ_PAYMENT_URL');
  return u.href;
}
export async function authorization(apiKey,secret,path,body,nonce) {
  const encoder=new TextEncoder();
  const key=await crypto.subtle.importKey('raw',encoder.encode(secret),{name:'HMAC',hash:'SHA-256'},false,['sign']);
  const signature=await crypto.subtle.sign('HMAC',key,encoder.encode(nonce+path+body));
  const hex=Array.from(new Uint8Array(signature),x=>x.toString(16).padStart(2,'0')).join('');
  return 'IYZWSv2 '+btoa(`apiKey:${apiKey}&randomKey:${nonce}&signature:${hex}`);
}
export async function providerRequest(config,path,payload,fetcher=fetch) {
  const body=JSON.stringify(payload),nonce=crypto.randomUUID().replaceAll('-','');
  const base=config.environment==='live'?'https://api.iyzipay.com':'https://sandbox-api.iyzipay.com';
  const response=await fetcher(base+path,{method:'POST',redirect:'error',signal:AbortSignal.timeout(18000),headers:{
    'Content-Type':'application/json','Accept':'application/json','x-iyzi-rnd':nonce,
    'Authorization':await authorization(config.apiKey,config.secret,path,body,nonce)},body});
  if(!response.ok)throw new Error('DPQ_PROVIDER_UNAVAILABLE');
  return response.json();
}
export function verifiedPayment(result,order) {
  // No redirect status, browser payload, card brand or client amount is trusted.
  if(result.status!=='success'||result.paymentStatus!=='SUCCESS')return {pending:true};
  if(Number(result.fraudStatus)!==1)return {pending:Number(result.fraudStatus)===0,rejected:Number(result.fraudStatus)===-1};
  if(result.basketId!==order.id||result.conversationId!==order.id||result.currency!==order.currency||
     minorUnits(result.price)!==order.amount_minor||minorUnits(result.paidPrice)!==order.amount_minor||
     typeof result.paymentId!=='string'||!result.paymentId)throw new Error('DPQ_PAYMENT_MISMATCH');
  const items=result.itemTransactions;
  if(!Array.isArray(items)||items.length!==1||items[0].itemId!==order.offer||minorUnits(items[0].price)!==order.amount_minor||
     ![1,2].includes(Number(items[0].transactionStatus))||!items[0].paymentTransactionId)throw new Error('DPQ_PAYMENT_MISMATCH');
  return {event:`iyzico:${order.environment}:${result.paymentId}`,transaction:String(items[0].paymentTransactionId)};
}
export function buyerPayload(input,user,ip) {
  const fields={};
  for(const [key,max] of Object.entries({name:80,surname:80,identityNumber:20,gsmNumber:20,address:300,city:80,country:80})) {
    const value=String(input?.[key]||'').trim();
    if(value.length<2||value.length>max||/[\u0000-\u001f]/.test(value))throw new Error('DPQ_BILLING_DETAILS');
    fields[key]=value;
  }
  if(!/^\+\d{10,15}$/.test(fields.gsmNumber)||!/^\d{6,20}$/.test(fields.identityNumber))throw new Error('DPQ_BILLING_DETAILS');
  return {id:user.id,name:fields.name,surname:fields.surname,email:user.email,gsmNumber:fields.gsmNumber,
    identityNumber:fields.identityNumber,registrationAddress:fields.address,city:fields.city,country:fields.country,ip};
}
