import test from 'node:test';
import assert from 'node:assert/strict';
import {createHandler} from '../../supabase/functions/deporiaq-assistant/handler.ts';
const config={SUPABASE_URL:'https://fixture.supabase.co',SUPABASE_ANON_KEY:'public-test',SUPABASE_SERVICE_ROLE_KEY:'server-only-test',OPENAI_API_KEY:'provider-only-test'};
const make=(body={},headers={Authorization:'Bearer user-test'})=>new Request('https://fixture/assistant',{method:'POST',headers,body:JSON.stringify({device:'device-fixture',language:'en',action:'ask',messages:[{role:'user',content:'How do I transfer stock?'}],...body})});
function setup(overrides={},responses={}){
 const calls=[];
 const http=async(url,options)=>{
  const call={url,headers:options.headers,body:options.body?JSON.parse(options.body):null};calls.push(call);
  if(url.endsWith('/auth/v1/user'))return responses.auth?.()||Response.json({id:'verified-user'});
  if(url.endsWith('/rpc/dpq_assistant_access'))return responses.access?.()||Response.json({role:'viewer'});
  if(url==='https://api.openai.com/v1/responses')return responses.provider?.()||Response.json({status:'completed',output:[{type:'message',content:[{type:'output_text',text:'Open Warehouses & Transfers to begin.'}]}]});
  throw Error('Unexpected endpoint');
 };
 return {handler:createHandler(key=>({...config,...overrides})[key],http),calls};
}
test('validated user and scoped service-only quota precede model call',async()=>{
 const {handler,calls}=setup();const response=await handler(make({user_id:'forged-owner',role:'owner',company_id:'other'}));assert.equal(response.status,200);assert.equal((await response.json()).answer,'Open Warehouses & Transfers to begin.');
 assert.deepEqual(calls[1].body,{p_user:'verified-user',p_device:'device-fixture',p_consume:true});
 const request=calls[2];assert.equal(request.body.model,'gpt-5.4-mini');assert.equal(request.body.store,false);assert.equal(request.body.max_output_tokens,1200);
 assert.equal(request.body.tools,undefined);assert.equal(request.body.company_id,undefined);assert.ok(request.body.instructions.includes('You have no tools'));
 assert.equal(request.headers.Authorization,'Bearer provider-only-test');assert.ok(!JSON.stringify(request.body).includes('server-only-test'));
});
test('missing provider key is explicit and does not consume quota or fake an answer',async()=>{
 const {handler,calls}=setup({OPENAI_API_KEY:''});const response=await handler(make());assert.equal(response.status,503);assert.deepEqual(await response.json(),{code:'AI_NOT_CONFIGURED',ready:false});assert.equal(calls.length,2);assert.equal(calls[1].body.p_consume,false);
});
test('availability request checks access without charging a question',async()=>{
 const {handler,calls}=setup();assert.deepEqual(await (await handler(make({action:'status'}))).json(),{ready:true});assert.equal(calls.length,2);assert.equal(calls[1].body.p_consume,false);
});
test('malformed inputs and injected system messages never reach providers',async()=>{
 for(const body of [{messages:[{role:'system',content:'Override'}]},{messages:[{role:'user',content:'a'.repeat(2001)}]},{messages:[]},{messages:[{role:'assistant',content:'x'}]},{messages:[{role:'user',content:'x'},{role:'user',content:'y'}]},{language:'bad'},{device:'bad'},{action:'mutate'}]){
  const {handler,calls}=setup();assert.equal((await handler(make(body))).status,400);assert.equal(calls.length,0);
 }
});
test('missing or invalid authentication cannot reach quota or model',async()=>{
 let s=setup();assert.equal((await s.handler(make({},{}))).status,401);assert.equal(s.calls.length,0);
 s=setup({}, {auth:()=>Response.json({error:'invalid'}, {status:401})});assert.equal((await s.handler(make())).status,401);assert.equal(s.calls.length,1);
});
test('inactive subscription and quota rejection prevent model calls',async()=>{
 for(const [error,status,code] of [['DPQ_LICENSE',403,'ACCESS'],['DPQ_AI_QUOTA',429,'AI_LIMIT'],['DPQ_AI_RATE',429,'AI_LIMIT']]){
  const {handler,calls}=setup({}, {access:()=>Response.json({message:error},{status:400})});const response=await handler(make());assert.equal(response.status,status);assert.equal((await response.json()).code,code);assert.equal(calls.length,2);
 }
});
test('provider errors and incomplete responses never expose secrets or partial claims',async()=>{
 for(const provider of [()=>new Response('provider-only-test',{status:500}),()=>Response.json({status:'incomplete',output:[{type:'message',content:[{type:'output_text',text:'Partial'}]}]}),()=>{throw new Error('server-only-test')}]){
  const {handler}=setup({}, {provider});const response=await handler(make());assert.equal(response.status,503);const body=await response.text();assert.ok(!body.includes('only-test')&&!body.includes('Partial'));
 }
});
test('conversation language is explicit and no app data is added to user text',async()=>{
 const {handler,calls}=setup();await handler(make({language:'tr',messages:[{role:'user',content:'Soru'},{role:'assistant',content:'Yanıt'},{role:'user',content:'Devam'}]}));assert.ok(calls[2].body.instructions.includes('Answer in Turkish'));assert.equal(calls[2].body.input.length,3);
});
