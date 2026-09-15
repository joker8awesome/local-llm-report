const fs=require('fs'),vm=require('vm'),assert=require('assert');
const path=require('path');
const html=fs.readFileSync(path.join(__dirname,'radar.html'),'utf8');
const scripts=[...html.matchAll(/<script>([\s\S]*?)<\/script>/g)].map(x=>x[1]);
const ids=new Map([...html.matchAll(/id="([^"]+)"/g)].map(x=>[x[1],{textContent:'',className:'',innerHTML:'',classList:{toggle(){},add(){},remove(){}}}]));
let reads=[],writes=[],fetches=[];
const context=vm.createContext({console,Date,Set,Math,JSON,encodeURIComponent,
 localStorage:{getItem(k){reads.push(k);return null},setItem(k,v){writes.push(k)},removeItem(k){writes.push(k)}},
 document:{querySelector(selector){assert(selector.startsWith('#'));assert(ids.has(selector.slice(1)),'missing selector '+selector);return ids.get(selector.slice(1))},documentElement:{setAttribute(){},removeAttribute(){},getAttribute(){return null}}},
 fetch:async url=>{fetches.push(url);
  // 발행 시각 표시(g077)가 publish_meta.json을 추가로 읽는다. 목록과 메타 둘 다 허용한다.
  assert(url.startsWith('./data/videos.json?')||url.startsWith('./data/publish_meta.json?'),'unexpected fetch '+url);
  if(url.startsWith('./data/publish_meta.json?')) return {ok:true,json:async()=>({generated_at:new Date(Date.now()-3*36e5).toISOString(),record_count:1,db_total:9,db_skipped:1})};
  return {ok:true,json:async()=>[{video_id:'fixture',title:'<script>bad</script>',status:'DISCOVERED',trend_score:1,source:'live'},{video_id:'hidden',title:'hidden',status:'SKIPPED'}]}}
});
(async()=>{
 for(const code of scripts)vm.runInContext(code,context);
 await new Promise(resolve=>setImmediate(resolve));
 assert.equal(fetches.length,2,'videos.json + publish_meta.json');
 assert(fetches.some(u=>u.startsWith('./data/publish_meta.json?')),'publish_meta fetched');
 // 3시간 전 발행이면 정상(ok) — 배너는 숨김이어야 한다.
 assert(ids.get('freshPill').className==='pill ok','fresh pill ok, got '+ids.get('freshPill').className);
 assert(ids.get('staleBanner').className.includes('hide'),'stale banner hidden when fresh');
 assert(ids.get('view').innerHTML.includes('data-vid="fixture"'));
 assert(!ids.get('view').innerHTML.includes('data-vid="hidden"'));
 assert(ids.get('view').innerHTML.includes('&lt;script&gt;bad&lt;/script&gt;'));
 assert(ids.get('view').innerHTML.includes('button disabled'));
 for(const token of ['data-contact','pendingContact','confirmContact','sendCommand','radar_skipped','id="modal"'])assert(!html.includes(token));
 assert.deepEqual(reads,['con_theme']);assert.deepEqual(writes,[]);
 for(const state of ['DISCOVERED','REVIEWED','PLANNED','PRODUCED','PUBLISHED','SKIPPED']) assert(vm.runInContext(`statusBadge('${state}')`,context).includes('statusbadge'));
 vm.runInContext('videos=[];render()',context);assert(ids.get('view').innerHTML.includes('표시할 후보가 없습니다'));
  // 26시간 초과면 경고 배너가 뜨고 pill이 bad가 된다.
 vm.runInContext("(async()=>{const old=fetch;globalThis.fetch=async u=>u.startsWith('./data/publish_meta.json?')?{ok:true,json:async()=>({generated_at:new Date(Date.now()-48*36e5).toISOString(),record_count:1,db_total:9})}:old(u);await loadMeta();})()",context);
 await new Promise(resolve=>setImmediate(resolve));
 assert.equal(ids.get('freshPill').className,'pill bad','stale pill bad, got '+ids.get('freshPill').className);
 assert(!ids.get('staleBanner').className.includes('hide'),'stale banner shown when stale');
 assert(ids.get('staleBanner').textContent.includes('멈춰 있습니다'),'stale banner text');
 console.log('PASS: offline DOM selectors, render, six labels, escaped title, skipped exclusion, disabled control, no credential access or command network, publish freshness');
})().catch(e=>{console.error(e);process.exit(1)});
