// Downloads full-size artwork for the Modern Collection in the background after the game opens.
// Files are kept in Cache Storage ("ygo-modern-art-v1"); the service workers serve them offline.
// Opt out with localStorage['ygo-modern-art']='off'. Safe to interrupt: the next launch resumes.
export const MODERN_ART_CACHE='ygo-modern-art-v1';
const artURL=id=>`https://images.ygoprodeck.com/images/cards/${id}.jpg`;
const MISSING_KEY='ygo-modern-art-missing',sleep=ms=>new Promise(r=>setTimeout(r,ms));
export const modernArtStatus={state:'idle',total:0,done:0,missing:0,failed:0,bytes:0,mode:'cache'};

function readMissing(){try{return new Set(JSON.parse(localStorage.getItem(MISSING_KEY)||'[]'))}catch{return new Set()}}
function writeMissing(set){try{localStorage.setItem(MISSING_KEY,JSON.stringify([...set]))}catch{}}

export async function startModernArtDownload(ids,{notify=()=>{},workers=3,gap=120}={}){
 try{if(localStorage.getItem('ygo-modern-art')==='off')return modernArtStatus}catch{}
 if(modernArtStatus.state==='running'||!ids?.length)return modernArtStatus;
 if(navigator.connection?.saveData){modernArtStatus.state='skipped-save-data';return modernArtStatus}
 const hasCache=typeof caches!=='undefined';
 let cache=null;if(hasCache){try{cache=await caches.open(MODERN_ART_CACHE)}catch{}}
 try{await navigator.storage?.persist?.()}catch{}
 const have=new Set();
 if(cache)for(const request of await cache.keys()){const m=/\/cards\/(\d+)\.jpg$/.exec(request.url);if(m)have.add(Number(m[1]))}
 const missing=readMissing(),queue=ids.filter(id=>!have.has(id)&&!missing.has(id));
 Object.assign(modernArtStatus,{state:'running',total:ids.length,done:have.size,missing:missing.size,failed:0,bytes:0,mode:cache?'cache':'prefetch'});
 if(!queue.length){modernArtStatus.state='complete';return modernArtStatus}
 try{const {usage=0,quota=0}=await navigator.storage?.estimate?.()||{};
  if(cache&&quota&&quota-usage<queue.length*90*1024){notify(`Modern card art needs about ${Math.ceil(queue.length*90/1024)} MB but this browser only has ${Math.floor((quota-usage)/1048576)} MB free. Downloading as much as fits.`)}}catch{}
 notify(`Downloading ${queue.length.toLocaleString()} modern card images in the background…`);
 let next=0,streak=0,corsFailures=0,aborted=false;
 const fetchOne=async id=>{
  if(modernArtStatus.mode==='prefetch'){ // No CORS access: warm the normal HTTP cache instead
   await new Promise((resolve,reject)=>{const img=new Image();img.onload=resolve;img.onerror=reject;img.src=artURL(id)});return 0}
  const response=await fetch(artURL(id),{mode:'cors',credentials:'omit'});
  if(response.status===404){missing.add(id);modernArtStatus.missing++;writeMissing(missing);return 0}
  if(!response.ok)throw Error('HTTP '+response.status);
  const size=Number(response.headers.get('content-length'))||0;
  await cache.put(artURL(id),response);return size};
 const worker=async()=>{
  while(!aborted){
   const id=queue[next++];if(id===undefined)return;
   if(navigator.onLine===false){aborted=true;return}
   try{const size=await fetchOne(id);modernArtStatus.done++;modernArtStatus.bytes+=size;streak=0}
   catch(error){
    if(error instanceof TypeError&&modernArtStatus.mode==='cache'&&++corsFailures>=3&&modernArtStatus.done===have.size){modernArtStatus.mode='prefetch';next=Math.max(0,next-corsFailures);corsFailures=-1e9;continue}
    modernArtStatus.failed++;if(++streak>=25){aborted=true;return}
    if(error?.name==='QuotaExceededError'){aborted=true;notify('Out of storage space for modern card art; downloaded images are kept.');return}}
   await sleep(gap)}};
 await Promise.all(Array.from({length:workers},worker));
 modernArtStatus.state=aborted?'paused':'complete';
 notify(aborted?'Modern card art download paused; it will resume next time you open the game.':`Modern card art ready (${modernArtStatus.done.toLocaleString()} cards${modernArtStatus.missing?`, ${modernArtStatus.missing} have no published image`:''}).`);
 return modernArtStatus}
