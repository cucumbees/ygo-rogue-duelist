export {BackupRegistry} from './backup.mjs';
export {ProgressRegistry} from './progress.mjs';
const headers={'Content-Type':'application/json','Access-Control-Allow-Origin':'*','Cache-Control':'no-store','Access-Control-Allow-Headers':'Content-Type, Authorization','Access-Control-Allow-Methods':'POST, OPTIONS'};
const reply=(status,data)=>new Response(JSON.stringify(data),{status,headers});
export default {async fetch(request,env){
 const path=new URL(request.url).pathname;
 if(request.method==='OPTIONS')return new Response(null,{status:204,headers});
 if(path.startsWith('/backup/')&&request.method==='POST')return env.BACKUP.get(env.BACKUP.idFromName('backups-v1')).fetch(request);
 if(path.startsWith('/progress/')&&request.method==='POST')return env.PROGRESS.get(env.PROGRESS.idFromName('progress-v1')).fetch(request);
 if(path==='/health')return reply(200,{service:'shadow-run-rooms',protocol:1});
 return reply(404,{error:'Unknown operation.'});
}};
