import fs from 'node:fs';import {fileURLToPath} from 'node:url';import assert from 'node:assert/strict';
import {MobileDuel,L,M} from './web/duel.js';import {I,R} from './web/engine.js';
const root=fileURLToPath(new URL('./web/',import.meta.url)),read=n=>JSON.parse(fs.readFileSync(root+n+'.json'));
const data=read('engine-data'),scripts=read('scripts');
const LINK_SPIDER=98978921,NORMAL=5053103; // Link Spider, Battle Ox (Normal)
const cards=[LINK_SPIDER,NORMAL].map(id=>({id,name:'c'+id,data:data[id]}));
const e=await new MobileDuel(cards).init([data,scripts]);
const setup=`Debug.AddCard(${NORMAL},0,0,LOCATION_HAND,0,POS_FACEDOWN)`;
const main=Array(40).fill(NORMAL);
const snap=e.start(main,main,8000,8000,5,1234,[LINK_SPIDER],[],'',5,null,5);
let pending=e.pending;
// advance to main phase 1 idle
for(let i=0;i<20&&pending&&pending.type!==M.SELECT_IDLECMD;i++){e.respond(e.auto(pending));pending=e.pending}
assert.equal(pending.type,M.SELECT_IDLECMD);
console.log('summons',pending.summons.length,'special',pending.special_summons.length);

const ox=pending.summons[0];assert.ok(ox,'a normal summon is available');
e.respond({type:R.SELECT_IDLECMD,action:I.SELECT_SUMMON,index:0}); // normal summon
pending=e.pending;
for(let i=0;i<10&&pending&&pending.type!==M.SELECT_IDLECMD;i++){e.respond(e.auto(pending));pending=e.pending}
console.log('after summon: special summons =',pending.special_summons.map(c=>c.code));
assert.ok(pending.special_summons.some(c=>c.code===LINK_SPIDER),'Link Summon offered in MR5');
const idx=pending.special_summons.findIndex(c=>c.code===LINK_SPIDER);
e.respond({type:R.SELECT_IDLECMD,action:I.SELECT_SPECIAL_SUMMON,index:idx});
for(let i=0;i<10&&e.pending&&e.pending.type!==M.SELECT_IDLECMD;i++){console.log('pending',e.pending.type);e.respond(e.auto(e.pending))}
const mz=e.query(0,L.MZONE);
console.log('MZONE',mz.map((c,i)=>c&&[i,c.code]).filter(Boolean));
assert.ok(mz.slice(5).some(c=>c&&c.code===LINK_SPIDER),'Link Spider landed in an Extra Monster Zone (seq 5/6)');
console.log('PASS');
