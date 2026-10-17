import {PGlite} from '@electric-sql/pglite';
import fs from 'node:fs';
import assert from 'node:assert/strict';
import {randomUUID} from 'node:crypto';
const db=new PGlite();
for(const file of ['tests/server/fixture.sql','tests/server/exported_legacy.sql','DEPORIAQ_CLOUD_0.24.0_MIGRATION.sql','server/007_counter_sales.sql','server/008_presence.sql','server/009_workspace.sql','server/010_support_dispatch.sql'])await db.exec(fs.readFileSync(file,'utf8'));
const c=randomUUID(),other=randomUUID(),owner=randomUUID(),admin=randomUUID(),viewer=randomUUID(),outsider=randomUUID(),l=randomUUID(),p=randomUUID();
for(const [id,name] of [[c,'Original Business'],[other,'Other Business']]){
 await db.query('insert into companies values($1,$2)',[id,name]);
 await db.query("insert into company_subscriptions(company_id,status,valid_until,plan_code) values($1,'active',now()+interval '32 days','duo')",[id]);
}
for(const [id,company,role] of [[owner,c,'owner'],[admin,c,'admin'],[viewer,c,'viewer'],[outsider,other,'owner']])await db.query('insert into company_members values($1,$2,$3,true,now())',[company,id,role]);
await db.query("insert into locations values($1,$2,'İzmir Karşıyaka','center',true)",[l,c]);await db.query('select dpq_enable($1,$2,$3)',[c,'duo',l]);
await db.query("select set_config('dpq.internal',$1,false)",[c]);await db.query("insert into products values($1,$2,'001234567','Elif Şafak Aşk',80,50,2,true)",[p,c]);await db.query('insert into inventory(company_id,product_id,location_id,quantity) values($1,$2,$3,8)',[c,p,l]);
await db.query("insert into dpq.workspace_records(company_id,kind,data,actor) values($1,'product',$2,$3)",[c,JSON.stringify({product_id:p,author:'Elif Şafak',shelf:'A-42'}),owner]);
await db.query("select set_config('dpq.internal',$1,false)",[other]);await db.query("insert into products values($1,$2,'001234567','Private book',80,50,2,true)",[randomUUID(),other]);
await db.query("select set_config('request.jwt.claim.sub',$1,false)",[owner]);await db.exec('set role authenticated');await db.query("select dpq_call('register','{}','device-experience')");await db.exec('reset role');
const beforeSubscriptions=(await db.query('select * from company_subscriptions order by company_id')).rows;
const beforeInventory=(await db.query('select * from inventory')).rows;
for(let i=0;i<2;i++)await db.exec(fs.readFileSync('server/011_experience.sql','utf8'));
assert.deepEqual((await db.query('select * from company_subscriptions order by company_id')).rows,beforeSubscriptions);assert.deepEqual((await db.query('select * from inventory')).rows,beforeInventory);
await db.exec('set role authenticated');
const profile=async(name=null,old=null)=>(await db.query('select dpq_company_profile($1,$2,$3) r',['device-experience',name,old])).rows[0].r;
assert.equal((await profile()).name,'Original Business');
await assert.rejects(()=>db.query("update companies set name='Bypass' where id=$1",[c]),/permission denied/);
assert.equal((await profile('İzmir Kitap Dünyası','Original Business')).name,'İzmir Kitap Dünyası');
assert.equal((await profile('İzmir Kitap Dünyası','Original Business')).name,'İzmir Kitap Dünyası');
await assert.rejects(()=>profile('Stale Name','Original Business'),/DPQ_CONFLICT/);
await assert.rejects(()=>profile('x','İzmir Kitap Dünyası'),/DPQ_INPUT/);
await assert.rejects(()=>profile('Bad\nName','İzmir Kitap Dünyası'),/DPQ_INPUT/);
for(const id of [admin,viewer]){await db.query("select set_config('request.jwt.claim.sub',$1,false)",[id]);assert.equal((await profile()).can_rename,false);await assert.rejects(()=>profile('Forbidden','İzmir Kitap Dünyası'),/DPQ_OWNER/);}
const search=async(q)=>(await db.query('select dpq_search($1,$2) r',[q,'device-experience'])).rows[0].r;
for(const query of ['ask','AŞK','elif safak','001234567','A-42']){const rows=await search(query);assert.equal(rows.length,1);assert.equal(rows[0].id,p);}
assert.equal((await search('001234567'))[0].rank,0);
assert.equal((await search('izmir karsiyaka'))[0].id,l);assert.deepEqual(await search('%_'),[]);assert.deepEqual(await search('a'),[]);assert.deepEqual(await search('Private'),[]);
await db.query("select set_config('request.jwt.claim.sub',$1,false)",[outsider]);await assert.rejects(()=>search('001234567'),/DPQ_LICENSE|DPQ_DEVICE/);
await assert.rejects(()=>db.query('select dpq_assistant_access($1,$2,true)',[owner,'device-experience']),/permission denied/);
await db.exec('reset role');assert.equal((await db.query("select count(*)::int n from dpq.audit where action='company_rename'")).rows[0].n,1);
await db.exec('set role service_role');
const access=(consume=true)=>db.query('select dpq_assistant_access($1,$2,$3)',[owner,'device-experience',consume]);
await access(false);await access();await assert.rejects(()=>access(),/DPQ_AI_RATE/);
await db.exec('reset role');await db.query("update dpq.assistant_usage set requests=50,last_request=now()-interval '10 seconds'");await db.exec('set role service_role');await assert.rejects(()=>access(),/DPQ_AI_QUOTA/);
await db.exec('reset role');await db.query("update company_subscriptions set valid_until=now()-interval '1 minute' where company_id=$1",[c]);await db.exec('set role service_role');await assert.rejects(()=>access(false),/DPQ_LICENSE/);
await db.close();console.log('PASS owner-only profile, audited/idempotent rename, stale-edit guard, bilingual scoped search, barcode ranking, preserved stock/subscriptions, service-only AI quotas');
