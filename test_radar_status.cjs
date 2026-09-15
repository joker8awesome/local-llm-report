const fs=require('fs'),vm=require('vm'),assert=require('assert');
const path=require('path');
const html=fs.readFileSync(path.join(__dirname,'radar.html'),'utf8');
const scripts=[...html.matchAll(/<script>([\s\S]*?)<\/script>/g)].map(x=>x[1]);
const ids=new Map([...html.matchAll(/id="([^"]+)"/g)].map(x=>[x[1],{textContent:'',className:'',innerHTML:'',classList:{toggle(){},add(){},remove(){}}}]));
let reads=[],writes=[],fetches=[];
const context=vm.createContext({console,Date,Set,Math,JSON,encodeURIComponent,
 localStorage:{getItem(k){reads.push(k);return null},setItem(k,v){writes.push(k)},removeItem(k){writes.push(k)}},
 document:{querySelector(selector){assert(selector.startsWith('#'));assert(ids.has(selector.slice(1)),'missing selector '+selector);return ids.get(selector.slice(1))},documentElement:{setAttribute(){},removeAttribute(){},getAttribute(){return null}}},
 fetch:async url=>{fetches.push(url);assert(url.startsWith('./data/videos.json?'));return {ok:true,json:async()=>[{video_id:'fixture',title:'<script>bad</script>',status:'DISCOVERED',trend_score:1,source:'live'},{video_id:'hidden',title:'hidden',status:'SKIPPED'}]}}
});
(async()=>{
 for(const code of scripts)vm.runInContext(code,context);
 await new Promise(resolve=>setImmediate(resolve));
 assert.equal(fetches.length,1);
 assert(ids.get('view').innerHTML.includes('data-vid="fixture"'));
 assert(!ids.get('view').innerHTML.includes('data-vid="hidden"'));
 assert(ids.get('view').innerHTML.includes('&lt;script&gt;bad&lt;/script&gt;'));
 assert(ids.get('view').innerHTML.includes('button disabled'));
 for(const token of ['data-contact','pendingContact','confirmContact','sendCommand','radar_skipped','id="modal"'])assert(!html.includes(token));
 assert.deepEqual(reads,['con_theme']);assert.deepEqual(writes,[]);
 for(const state of ['DISCOVERED','REVIEWED','PLANNED','PRODUCED','PUBLISHED','SKIPPED']) assert(vm.runInContext(`statusBadge('${state}')`,context).includes('statusbadge'));
 vm.runInContext('videos=[];render()',context);assert(ids.get('view').innerHTML.includes('표시할 후보가 없습니다'));
 console.log('PASS: offline DOM selectors, render, six labels, escaped title, skipped exclusion, disabled control, no credential access or command network');
})().catch(e=>{console.error(e);process.exit(1)});
