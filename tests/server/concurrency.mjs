// Native PostgreSQL required. Genuine separate sessions, never substituted by mocks.
import {Client} from 'pg';import {randomUUID} from 'node:crypto';import assert from 'node:assert/strict';
import fs from 'node:fs';import path from 'node:path';
if(!process.env.DPQ_TEST_DATABASE_URL)throw Error('DPQ_TEST_DATABASE_URL required');
const connect=async()=>{const c=new Client({connectionString:process.env.DPQ_TEST_DATABASE_URL});await c.connect();return c};
const admin=await connect(),C=randomUUID(),U=randomUUID(),P=randomUUID(),L=randomUUID();
await admin.query("insert into companies values($1,'Concurrent')",[C]);await admin.query("insert into company_members values($1,$2,'owner',true,now())",[C,U]);
await admin.query("insert into company_subscriptions(company_id,status,valid_until,plan_code) values($1,'active',now()+interval '30 days','single')",[C]);
await admin.query("insert into locations values($1,$2,'Merkez','center',true)",[L,C]);
await admin.query("insert into products values($1,$2,'LAST','Last item',100,50,0,true)",[P,C]);
await admin.query('insert into inventory(company_id,product_id,location_id,quantity) values($1,$2,$3,1)',[C,P,L]);
await admin.query("select dpq_enable($1,'single',$2)",[C,L]);
const clients=await Promise.all(Array.from({length:12},connect));
for(const c of clients){await c.query("select set_config('request.jwt.claim.sub',$1,false)",[U]);await c.query('set role authenticated')}
const call=(client,action,payload,device)=>(client.query('select dpq_call($1,$2::jsonb,$3) r',[action,JSON.stringify(payload),device]));
const registrations=await Promise.allSettled(clients.map((c,i)=>call(c,'register',{name:'PC'},'test-device-'+i)));
assert.equal(registrations.filter(x=>x.status==='fulfilled').length,1,'Exactly one device slot must be granted');
const winner=registrations.findIndex(x=>x.status==='fulfilled'),device='test-device-'+winner;
const channel=(await call(clients[0],'channel_save',{request_id:randomUUID(),name:'web',locations:[{id:L,buffer:0}]},device)).rows[0].r.id;
const competing=await Promise.allSettled(clients.map((c,i)=>i%2
 ?call(c,'sale',{request_id:randomUUID(),product_id:P,location_id:L,quantity:1},device)
 :call(c,'reserve',{request_id:randomUUID(),channel_id:channel,reference:'order-'+i,customer:'Test',shipping:'split',items:[{product_id:P,quantity:1}]},device)));
assert.equal(competing.filter(x=>x.status==='fulfilled').length,1,'Exactly one POS or web order may take last item');
const p2=randomUUID();await admin.query("select set_config('dpq.internal',$1,false)",[C]);
await admin.query("insert into products values($1,$2,'RETRY','Retry item',100,50,0,true)",[p2,C]);
await admin.query('insert into inventory(company_id,product_id,location_id,quantity) values($1,$2,$3,10)',[C,p2,L]);
await admin.query("select set_config('dpq.internal','',false)");
const payload={request_id:randomUUID(),product_id:p2,location_id:L,quantity:1};
const retries=await Promise.all(clients.map(c=>call(c,'sale',payload,device)));
assert.equal(retries.length,12);assert.equal(Number((await admin.query('select quantity from inventory where product_id=$1',[p2])).rows[0].quantity),9,'12 retries must sell once');
await Promise.all(clients.map(c=>c.end()));await admin.end();
const out=path.resolve(import.meta.dirname,'../../test-results');fs.mkdirSync(out,{recursive:true});
fs.writeFileSync(path.join(out,'concurrency.json'),JSON.stringify({engine:'native PostgreSQL, twelve separate sessions',passed:['one device slot','POS versus reservation last item','12 simultaneous retries sell once']},null,2));
console.log('PASS: three native PostgreSQL concurrency scenarios');
