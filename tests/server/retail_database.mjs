import {PGlite} from '@electric-sql/pglite';
import {Client} from 'pg';
export async function database(){
 if(!process.env.DPQ_TEST_DATABASE_URL)return new PGlite();
 const url=new URL(process.env.DPQ_TEST_DATABASE_URL);
 if(!['localhost','127.0.0.1'].includes(url.hostname)||url.pathname!='/deporiaq_test')throw new Error('Retail test accepts only the isolated local CI database');
 const admin=new Client({connectionString:url.href});await admin.connect();
 const name='dpq_retail_'+process.pid;await admin.query('CREATE DATABASE '+name);
 url.pathname='/'+name;const connectionString=url.href;const client=new Client({connectionString});await client.connect();
 return {
  exec:sql=>client.query(sql.replace(/create role (anon|authenticated|service_role);/g,"do $$$$ begin create role $1; exception when duplicate_object then null; end $$$$;")),
  query:(...args)=>client.query(...args),
  parallel:async (user,payloads)=>Promise.allSettled(payloads.map(async payload=>{
    const c=new Client({connectionString});await c.connect();try{
      await c.query('begin');await c.query("select set_config('request.jwt.claim.sub',$1,true)",[user]);await c.query('set local role authenticated');
      const result=await c.query("select dpq_retail('retail_sale',$1,'retail-device') r",[JSON.stringify(payload)]);await c.query('commit');return result.rows[0].r;
    }catch(e){await c.query('rollback');throw e;}finally{await c.end();}
  })),
  close:async()=>{await client.end();await admin.query('DROP DATABASE '+name);await admin.end();}
 };
}
