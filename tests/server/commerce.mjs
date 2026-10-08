import {PGlite} from '@electric-sql/pglite';
import fs from 'node:fs';
import path from 'node:path';
import assert from 'node:assert/strict';
import {randomUUID} from 'node:crypto';
const root=path.resolve(import.meta.dirname,'../..');
let db;
if(process.env.DPQ_TEST_DATABASE_URL){
 const {Client}=await import('pg');const pg=new Client({connectionString:process.env.DPQ_TEST_DATABASE_URL});await pg.connect();
 db={query:(...a)=>pg.query(...a),exec:(s)=>pg.query(s),close:()=>pg.end()};
}else db=new PGlite();
await db.exec(fs.readFileSync(path.join(import.meta.dirname,'fixture.sql'),'utf8'));
await db.exec(fs.readFileSync(path.join(import.meta.dirname,'exported_legacy.sql'),'utf8'));
await db.exec(fs.readFileSync(path.join(root,'DEPORIAQ_CLOUD_0.24.0_MIGRATION.sql'),'utf8'));
const C=randomUUID(),U=randomUUID(),P=randomUUID(),L=[randomUUID(),randomUUID(),randomUUID(),randomUUID()];
await db.query('insert into companies values($1,$2)',[C,'Test']);
await db.query("insert into company_members values($1,$2,'owner',true,now())",[C,U]);
await db.query("insert into company_subscriptions(company_id,status,valid_until,plan_code) values($1,'active',now()+interval '30 days','duo')",[C]);
for(let i=0;i<4;i++) await db.query('insert into locations values($1,$2,$3,$4,true)',[L[i],C,['Merkez','A','B','C'][i],i?'branch':'center']);
await db.query("insert into products values($1,$2,'X','X kitabı',100,60,0,true)",[P,C]);
for(let i=0;i<4;i++) await db.query('insert into inventory(company_id,product_id,location_id,quantity) values($1,$2,$3,$4)',[C,P,L[i],[2,1,1,3][i]]);
await db.query('select public.dpq_enable($1,$2,$3)',[C,'duo',L[0]]);
await db.query("select set_config('request.jwt.claim.sub',$1,false)",[U]);
await db.exec('set role authenticated');
const call=async(action,payload={},device='device-test-1')=>(await db.query('select public.dpq_call($1,$2::jsonb,$3) r',[action,JSON.stringify(payload),device])).rows[0].r;
const cmd=(a,p={})=>call(a,{...p,request_id:randomUUID()});
let passes=[];
async function test(name,fn){ await fn(); passes.push(name); console.log('PASS',name); }
async function rejects(fn,text){await assert.rejects(fn,e=>String(e).includes(text));}
await test('Unauthenticated status denied',async()=>{await db.exec('reset role');await db.query("select set_config('request.jwt.claim.sub','',false)");await rejects(()=>call('status'),'DPQ_AUTH');await db.query("select set_config('request.jwt.claim.sub',$1,false)",[U]);await db.exec('set role authenticated');});
await test('Device cap and idempotent registration',async()=>{for(let i=1;i<=3;i++) await call('register',{name:'PC'},'device-test-'+i);await call('register',{name:'PC'});await rejects(()=>call('register',{name:'PC'},'device-test-4'),'DPQ_LIMIT');});
const channel=(await cmd('channel_save',{name:'WhatsApp',locations:L.map(id=>({id,buffer:0}))})).id;
const request={request_id:randomUUID(),channel_id:channel,reference:'ORDER-4',customer:'Test',shipping:'consolidate',items:[{product_id:P,quantity:4}]};
let order;
await test('Center 2 + C 2 reserved, A/B unchanged',async()=>{order=(await call('reserve',request)).id;const s=await call('snapshot');const a=s.orders.find(o=>o.id===order).allocations;assert.equal(a.length,2);assert.deepEqual(a.map(x=>[x.location_id,x.quantity]).sort(),[[L[0],2],[L[3],2]].sort());assert.equal(s.inventory.reduce((a,x)=>a+Number(x.available),0),3);});
await test('Exact retry returns same order, changed retry denied',async()=>{assert.equal((await call('reserve',request)).id,order);await rejects(()=>call('reserve',{...request,customer:'changed'}),'DPQ_REPLAY');});
await test('POS cannot sell reserved stock',async()=>{await rejects(()=>cmd('sale',{product_id:P,location_id:L[0],quantity:1}),'DPQ_STOCK');});
await test('Insufficient order rolls back all partial allocations',async()=>{await rejects(()=>cmd('reserve',{...request,reference:'TOO-MANY',items:[{product_id:P,quantity:99}]}),'DPQ_STOCK');assert.equal((await call('snapshot')).orders.length,1);});
await test('Manual prepare, transit, receipt preserve reservations',async()=>{await cmd('order_prepare',{order_id:order});let a=(await call('snapshot')).orders[0].allocations.find(x=>x.location_id===L[3]);await cmd('allocation_dispatch',{order_id:order,allocation_id:a.id});await rejects(()=>cmd('order_cancel',{order_id:order}),'DPQ_STATE');await cmd('allocation_receive',{order_id:order,allocation_id:a.id});const s=await call('snapshot');assert.equal(s.inventory.find(x=>x.location_id===L[0]).available,0);});
await test('Ship all allocations and return once after inspection',async()=>{for(const a of (await call('snapshot')).orders[0].allocations)await cmd('allocation_ship',{order_id:order,allocation_id:a.id,carrier:'Test',tracking:'123'});assert.equal((await call('snapshot')).orders[0].status,'shipped');const a=(await call('snapshot')).orders[0].allocations[0];await rejects(()=>cmd('allocation_return',{order_id:order,allocation_id:a.id}),'DPQ_RETURN');await cmd('allocation_return',{order_id:order,allocation_id:a.id,inspected:true});await rejects(()=>cmd('allocation_return',{order_id:order,allocation_id:a.id,inspected:true}),'DPQ_STATE');});
await test('Direct writes/legacy path blocked even as table owner',async()=>{await db.exec('reset role');await rejects(()=>db.query('update inventory set quantity=99 where company_id=$1',[C]),'DPQ_SERVER_ONLY');await db.exec('set role authenticated');});
await test('Expiry denies sales but support still records pending mail',async()=>{await db.exec('reset role');await db.query("update company_subscriptions set valid_until=now()-interval '1 second' where company_id=$1",[C]);await db.exec('set role authenticated');await rejects(()=>cmd('sale',{product_id:P,location_id:L[1],quantity:1}),'DPQ_LICENSE');const s=await cmd('support',{subject:'Yardım',message:'Test destek mesajı',contact:'test@example.com'});assert.equal(s.mail_status,'pending');});
await test('Committed result can be reconciled after license expires',async()=>{
 const status=await call('operation_status',{request_id:request.request_id});assert.equal(status.found,true);assert.equal(status.result.id,order);
});
await test('Customer cannot activate subscription via payment RPC',async()=>{await rejects(()=>db.query('select public.dpq_apply_payment($1,$2,$3,$4)',['fake',randomUUID(),100,'TRY']),'permission denied');});
await test('Verified adapter rejects wrong amount and duplicate does not extend',async()=>{await db.exec('reset role');const id=randomUUID();await db.query("insert into dpq.checkout_orders(id,company_id,plan,amount_minor,period_end) values($1,$2,'duo',10000,now()+interval '30 days')",[id,C]);await db.exec('set role service_role');await rejects(()=>db.query('select public.dpq_apply_payment($1,$2,$3,$4)',['event',id,1,'TRY']),'Payment mismatch');await db.query('select public.dpq_apply_payment($1,$2,$3,$4)',['event',id,10000,'TRY']);const r=await db.query('select public.dpq_apply_payment($1,$2,$3,$4) r',['event',id,10000,'TRY']);assert.equal(r.rows[0].r.duplicate,true);await db.exec('set role authenticated');});
await test('Renewal cancellation preserves paid period',async()=>{const before=await call('status');await cmd('renewal',{renew:false});const after=await call('status');assert.equal(after.allowed,true);assert.equal(after.valid_until,before.valid_until);assert.equal(after.renew,false);});
await test('Disabled device cannot transact',async()=>{await cmd('device_disable',{code:'device-test-2'});await rejects(()=>call('snapshot',{},'device-test-2'),'DPQ_DEVICE');});
await test('Archived channel rejects new orders and preserves history',async()=>{await cmd('channel_archive',{channel_id:channel});await rejects(()=>cmd('reserve',{...request,reference:'NEW'}),'DPQ_CHANNEL');assert.equal((await call('snapshot')).orders.length,1);});

await test('Read-only member cannot sell or change package',async()=>{
 await db.exec('reset role');await db.query("update company_members set role='viewer' where user_id=$1",[U]);await db.exec('set role authenticated');
 await rejects(()=>cmd('sale',{product_id:P,location_id:L[1],quantity:1}),'DPQ_ROLE');
 await rejects(()=>cmd('renewal',{renew:true}),'DPQ_ROLE');
 await db.exec('reset role');await db.query("update company_members set role='owner' where user_id=$1",[U]);await db.exec('set role authenticated');
});
await test('Cross-company product cannot be sold',async()=>{
 await rejects(()=>cmd('sale',{product_id:randomUUID(),location_id:L[1],quantity:1}),'DPQ_PRODUCT');
});
await test('Trial lasts thirty days and reinstall cannot reset it',async()=>{
 await db.exec('reset role');const c2=randomUUID();await db.query("insert into companies values($1,'Trial')",[c2]);
 await db.exec('set role service_role');await db.query('select dpq_start_trial($1,$2)',[c2,'verified-identity-hash-long-enough-001']);
 await rejects(()=>db.query('select dpq_start_trial($1,$2)',[c2,'verified-identity-hash-long-enough-001']),'Existing subscription');
 await db.exec('reset role');const days=(await db.query("select extract(epoch from (expires_at-started_at))/86400 n from dpq.trial_claims where company_id=$1",[c2])).rows[0].n;assert.equal(Number(days),30);
 const c3=randomUUID();await db.query("insert into companies values($1,'Repeat')",[c3]);await db.exec('set role service_role');
 await rejects(()=>db.query('select dpq_start_trial($1,$2)',[c3,'verified-identity-hash-long-enough-001']),'duplicate key');await db.exec('set role authenticated');
});
await test('Expired unpaid reservation releases stock',async()=>{
 const ch=(await cmd('channel_save',{name:'Phone',locations:[{id:L[1],buffer:0}]})).id;
 const o=(await cmd('reserve',{channel_id:ch,reference:'EXP',customer:'Test',shipping:'split',items:[{product_id:P,quantity:1}]})).id;
 await db.exec('reset role');await db.query("update dpq.orders set expires_at=now()-interval '1 second' where id=$1",[o]);await db.exec('set role authenticated');
 const s=await call('snapshot');assert.equal(s.orders.find(x=>x.id===o).status,'expired');assert.equal(s.inventory.find(x=>x.location_id===L[1]).available,1);
});
await test('Support outbox is private, leased and retryable',async()=>{
 await rejects(()=>db.query('select dpq_claim_support()'),'permission denied');await db.exec('set role service_role');
 const ticket=(await db.query('select dpq_claim_support() r')).rows[0].r;assert.ok(ticket.lease);
 assert.equal((await db.query('select dpq_claim_support() r')).rows[0].r,null);
 assert.equal((await db.query('select dpq_finish_support($1,$2,false) r',[ticket.id,randomUUID()])).rows[0].r,false);
 assert.equal((await db.query('select dpq_finish_support($1,$2,true) r',[ticket.id,ticket.lease])).rows[0].r,true);
 await db.exec('set role authenticated');
});
await test('Strict read gate expires even with old grace period',async()=>{
 await db.exec('reset role');await db.query("update company_subscriptions set status='past_due',valid_until=now()-interval '1 day',grace_until=now()+interval '1 day' where company_id=$1",[C]);await db.exec('set role authenticated');
 assert.equal((await db.query('select dpq_read_allows($1) r',[C])).rows[0].r,false);
});
await test('Client table-wide privileges removed; truncate denied and rows preserved',async()=>{
 await db.exec('reset role');
 const before=(await db.query('select count(*)::int n from inventory')).rows[0].n;
 for(const role of ['anon','authenticated']) {
  for(const table of ['companies','company_members','company_subscriptions','locations','products','inventory','cloud_devices']) {
   for(const privilege of ['TRUNCATE','REFERENCES','TRIGGER']) {
    const result=await db.query('select has_table_privilege($1,$2,$3) allowed',[role,'public.'+table,privilege]);
    assert.equal(result.rows[0].allowed,false,`${role} ${table} ${privilege}`);
   }
  }
  await db.exec('set role '+role);
  await rejects(()=>db.query('truncate public.inventory'),'permission denied');
  await db.exec('reset role');
 }
 assert.equal((await db.query('select count(*)::int n from inventory')).rows[0].n,before);
});
await test('Exported legacy RPCs cannot bypass migrated-company guard',async()=>{
 await db.exec('reset role');
 const before=(await db.query('select location_id,quantity from inventory where company_id=$1 order by location_id',[C])).rows;
 await db.exec('set role authenticated');
 await rejects(()=>db.query("select apply_stock_movement($1,$2,$3,'increase',1)",[C,L[1],P]),'DPQ_SERVER_ONLY');
 await rejects(()=>db.query("select apply_stock_movement_v2($1,$2,$3,1,'increase','purchase',$4)",[C,P,L[1],randomUUID()]),'DPQ_SERVER_ONLY');
 await rejects(()=>db.query("select apply_stock_transfer_v2($1,$2,$3,$4,1,$5)",[C,P,L[1],L[2],randomUUID()]),'DPQ_SERVER_ONLY');
 await db.exec('reset role');
 assert.deepEqual((await db.query('select location_id,quantity from inventory where company_id=$1 order by location_id',[C])).rows,before);
 assert.equal(Number((await db.query('select count(*) n from cloud_operations')).rows[0].n),0);
 assert.equal(Number((await db.query('select count(*) n from stock_movements')).rows[0].n),0);
});
await test('Enabling standard subscription preserves paid expiry',async()=>{
 await db.exec('reset role');const c=randomUUID(),l=randomUUID();
 await db.query("insert into companies values($1,'Existing paid company')",[c]);
 await db.query("insert into locations values($1,$2,'Merkez Depo','center',true)",[l,c]);
 await db.query("insert into company_subscriptions(company_id,status,valid_until,plan_code) values($1,'active','2027-09-30T21:15:17Z','standard')",[c]);
 const before=(await db.query('select status,valid_until from company_subscriptions where company_id=$1',[c])).rows[0];
 await db.exec('set role service_role');await db.query('select dpq_enable($1,$2,$3)',[c,'single',l]);
 await db.exec('reset role');const after=(await db.query('select status,valid_until,plan_code from company_subscriptions where company_id=$1',[c])).rows[0];
 assert.deepEqual({status:after.status,valid_until:after.valid_until},before);assert.equal(after.plan_code,'single');
});
await test('Unmigrated legacy RPC denies expired, viewer and foreign location writes',async()=>{
 await db.exec('reset role');const c=randomUUID(),u=randomUUID(),p=randomUUID(),l=randomUUID();
 await db.query("insert into companies values($1,'Legacy paid')",[c]);
 await db.query("insert into company_members values($1,$2,'owner',true,now())",[c,u]);
 await db.query("insert into company_subscriptions(company_id,status,valid_until,plan_code) values($1,'active',now()+interval '1 day','standard')",[c]);
 await db.query("insert into locations values($1,$2,'Center','center',true)",[l,c]);
 await db.query("insert into products values($1,$2,'TEST','Test',1,1,0,true)",[p,c]);
 await db.query("select set_config('request.jwt.claim.sub',$1,false)",[u]);await db.exec('set role authenticated');
 const old=()=>db.query("select apply_stock_movement_v2($1,$2,$3,1,'increase','purchase',$4)",[c,p,l,randomUUID()]);
 await old();
 await rejects(()=>db.query("select apply_stock_movement_v2($1,$2,$3,1,'increase','purchase',$4)",[c,p,L[0],randomUUID()]),'DPQ_LOCATION');
 await db.exec('reset role');await db.query("update company_members set role='viewer' where company_id=$1",[c]);await db.exec('set role authenticated');
 await rejects(()=>db.query("select apply_stock_movement($1,$2,$3,'increase',1)",[c,l,p]),'DPQ_ROLE');
 await db.exec('reset role');await db.query("update company_members set role='owner' where company_id=$1",[c]);await db.query("update company_subscriptions set valid_until=now()-interval '1 second' where company_id=$1",[c]);await db.exec('set role authenticated');
 await rejects(old,'DPQ_LICENSE');
 await rejects(()=>db.query("select apply_stock_transfer_v2($1,$2,$3,$4,1,$5)",[c,p,l,L[0],randomUUID()]),'DPQ_LICENSE');
 await rejects(()=>db.query("select apply_stock_movement($1,$2,$3,'increase',1)",[c,l,p]),'DPQ_LICENSE');
 await db.exec('reset role');assert.equal(Number((await db.query('select quantity from inventory where company_id=$1',[c])).rows[0].quantity),1);
});
await db.close();
fs.mkdirSync(path.join(root,'test-results'),{recursive:true});fs.writeFileSync(path.join(root,'test-results','server-tests.json'),JSON.stringify({engine:process.env.DPQ_TEST_DATABASE_URL?'PostgreSQL native':'PGlite PostgreSQL WASM; single connection, NOT multi-session concurrency proof',passed:passes},null,2));
