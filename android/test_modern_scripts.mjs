// Loads every Modern Collection card's Lua script in the real core and records the ones that raise errors.
// Writes web/modern-script-errors.json (consumed by tools/build_modern_pack.py to drop broken cards).
import fs from 'node:fs';import {fileURLToPath} from 'node:url';
import {MobileDuel} from './web/duel.js';
const root=fileURLToPath(new URL('./web/',import.meta.url)),read=n=>JSON.parse(fs.readFileSync(root+n+'.json'));
const data=read('engine-data'),scripts=read('scripts');
const modern=JSON.parse(fs.readFileSync(fileURLToPath(new URL('../data/modern-cards.json',import.meta.url))));
const EXTRA=0x4802040,bad=new Set(),origError=console.error;console.error=()=>{};
const e=await new MobileDuel(modern.map(c=>({id:c.id,name:c.name,data:c.data}))).init([data,scripts]);
const BATCH=Number(process.env.BATCH||250);let n=0;
for(let i=0;i<modern.length;i+=BATCH){
 const batch=modern.slice(i,i+BATCH),main=batch.filter(c=>!(c.data.type&EXTRA)).map(c=>c.id),extra=batch.filter(c=>c.data.type&EXTRA).map(c=>c.id);
 e.errors=[];
 try{e.start(main.length?main:[89631139],[89631139],8000,8000,0,7,extra,[],'',0,null,5)}catch(err){e.errors.push(String(err))}
 for(const text of e.errors){const m=String(text).match(/c(\d+)\.lua/);if(m&&modern.some(c=>c.id===+m[1]))bad.add(+m[1])}
 n+=e.errors.length;
 if(i%(BATCH*10)===0)process.stderr.write(`batch ${i}/${modern.length} errors so far ${n} bad ${bad.size}\n`);
 e.destroy?.();
}
console.error=origError;
fs.writeFileSync(root+'modern-script-errors.json',JSON.stringify([...bad].sort((a,b)=>a-b)));
console.log('cards tested',modern.length,'raw errors',n,'cards with script errors',bad.size);
