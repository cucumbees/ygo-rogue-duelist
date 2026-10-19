import assert from 'node:assert/strict';
const store=new Map(),cache={keys:async()=>[...store.keys()].map(url=>({url})),put:async(u,r)=>{store.set(u,r)}};
globalThis.caches={open:async()=>cache};globalThis.localStorage={_d:{},getItem(k){return this._d[k]??null},setItem(k,v){this._d[k]=v}};
Object.defineProperty(globalThis,'navigator',{value:{onLine:true,storage:{persist:async()=>true,estimate:async()=>({usage:0,quota:1e12})}},configurable:true});
let calls=0;globalThis.fetch=async url=>{calls++;const id=Number(/(\d+)\.jpg/.exec(url)[1]);if(id===13)return {ok:false,status:404,headers:new Headers()};return {ok:true,status:200,headers:new Headers({'content-length':'100'})}};
const {startModernArtDownload,modernArtStatus}=await import('./web/modern-art.js');
const msgs=[];const ids=Array.from({length:40},(_,i)=>i+1);
await startModernArtDownload(ids,{notify:m=>msgs.push(m),gap:0});
assert.equal(modernArtStatus.state,'complete');assert.equal(store.size,39);assert.equal(modernArtStatus.missing,1);
const first=calls;modernArtStatus.state='idle';await startModernArtDownload(ids,{notify:m=>msgs.push(m),gap:0});
assert.equal(calls,first,'second launch downloads nothing (cached + known-missing skipped)');
// outage: every request fails -> pauses instead of hammering
store.clear();localStorage._d={};modernArtStatus.state='idle';calls=0;globalThis.fetch=async()=>{throw new Error('net')};
await startModernArtDownload(Array.from({length:200},(_,i)=>i+1),{notify:m=>msgs.push(m),gap:0,workers:1});
assert.equal(modernArtStatus.state,'paused');assert.ok(calls<=30,'stopped after repeated failures, calls='+calls);
console.log('PASS downloader:',msgs.join(' | ').slice(0,260));
