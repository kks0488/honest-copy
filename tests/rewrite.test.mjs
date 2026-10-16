import test from 'node:test';
import assert from 'node:assert/strict';
import { Readable } from 'node:stream';
import { rewrite, createHandler, getMode, DEFAULT_BASE_URL } from '../server/rewrite.mjs';
import { analyze, samples } from '../src/rules.mjs';
const body={text:samples.en,findingId:analyze(samples.en).findings[0].id};
// A test-only placeholder; not a credential and never used to call a provider.
const configured={LLM_API_KEY:'test-placeholder'};
const completion=content=>new Response(JSON.stringify({id:'demo-completion',object:'chat.completion',choices:[{index:0,message:{role:'assistant',content},finish_reason:'stop'}]}));
test('no-key demo uses actual rule template and never calls provider',async()=>{
  const result=await rewrite(body,{},()=>{throw new Error('Must not call');});
  assert.equal(result.mode,'template');assert.equal(result.replacement,'is designed for everyday care');
  assert.equal(getMode({LLM_API_KEY:' '}),'template');
});
test('OpenAI-compatible request and schema fixture, configured mode automatic',async()=>{
  let called=false;
  const result=await rewrite(body,configured,async(url,options)=>{
    called=true;assert.equal(String(url),DEFAULT_BASE_URL+'chat/completions');
    assert.equal(options.headers.Authorization,'Bearer test-placeholder');
    const payload=JSON.parse(options.body);assert.equal(payload.messages[1].role,'user');
    assert.equal(payload.model,'nvidia/Nemotron-3_5-Lightning');
    assert.deepEqual(payload.chat_template_kwargs,{enable_thinking:false});
    assert.deepEqual(payload.response_format,{type:'json_object'});
    assert.equal(payload.max_tokens,256);
    assert.equal(JSON.parse(payload.messages[1].content).selectedPhrase,'cures acne in 3 days');
    assert.ok(options.signal);return completion('{"replacement":"supports an everyday care routine"}');
  });
  assert.equal(called,true);assert.equal(result.mode,'live');assert.equal(getMode(configured),'live');
});
test('custom compatible base and model honored',async()=>{
  await rewrite(body,{...configured,LLM_BASE_URL:'https://provider.example/v1',LLM_MODEL:'configured-model'},async(url,opts)=>{
    assert.equal(String(url),'https://provider.example/v1/chat/completions');assert.equal(JSON.parse(opts.body).model,'configured-model');
    assert.equal(JSON.parse(opts.body).chat_template_kwargs,undefined);
    return completion('{"replacement":"is intended for everyday care"}');
  });
});
for (const content of [
  '<think>{"replacement":"cures cancer"}</think>{"replacement":"supports everyday care"}',
  '```json\n{"replacement":"supports everyday care"}\n```',
  'Here is the wording: {"replacement":"supports everyday care"}',
]) test('final content accepts JSON wrappers without exposing reasoning: '+content.slice(0,12),async()=>{
  const result=await rewrite(body,configured,async()=>completion(content));
  assert.equal(result.mode,'live');assert.equal(result.replacement,'supports everyday care');
});
test('reasoning-only and truncated replies visibly fall back',async()=>{
  for(const message of [
    {message:{content:null,reasoning_content:'{"replacement":"supports everyday care"}'},finish_reason:'stop'},
    {message:{content:'<think>{"replacement":"supports everyday care"}'},finish_reason:'stop'},
    {message:{content:'{"replacement":"supports everyday care"}'},finish_reason:'length'},
  ]) {
    const result=await rewrite(body,configured,async()=>new Response(JSON.stringify({choices:[message]})));
    assert.equal(result.mode,'template');assert.match(result.notice,/local template/);
  }
});
test('only numeric provider usage is returned, never reasoning or raw provider metadata',async()=>{
  const result=await rewrite(body,configured,async()=>new Response(JSON.stringify({choices:[{message:{content:'{"replacement":"supports everyday care"}',reasoning_content:'private reasoning'}}],usage:{prompt_tokens:12,completion_tokens:8,total_tokens:20,detail:'private'}})));
  assert.deepEqual(result.usage,{prompt_tokens:12,completion_tokens:8,total_tokens:20});
  assert.ok(!JSON.stringify(result).includes('private'));
});
for(const [name,provider] of [
  ['network',async()=>{throw new Error('secret provider detail');}],
  ['timeout',async()=>{throw new DOMException('timeout','TimeoutError');}],
  ['HTTP error',async()=>new Response('failure',{status:429})],
  ['invalid schema',async()=>completion('not JSON')],
  ['missing choices',async()=>new Response('{}')],
  ['risky rewrite',async()=>completion('{"replacement":"cures cancer"}')],
  ['invented numeric fact',async()=>completion('{"replacement":"is used by 9000 doctors"}')],
  ['HTML',async()=>completion('{"replacement":"<b>healthy</b>"}')],
  ['oversized output',async()=>new Response('a'.repeat(33000))],
])test(`${name} falls back honestly`,async()=>{
  const r=await rewrite(body,configured,provider);assert.equal(r.mode,'template');assert.match(r.notice,/local template/);assert.ok(!r.notice.includes('secret provider'));
});
test('input validation rejects missing/overlong/stale/forged finding',async()=>{
  for(const bad of [null,{}, {text:'a'.repeat(5001),findingId:'x'}, {text:'hello',findingId:body.findingId}, {...body,findingId:'fake'}]) await assert.rejects(rewrite(bad,{}));
});
test('Korean schema fixture preserves Korean response',async()=>{
  const korean={text:samples.ko,findingId:analyze(samples.ko).findings[0].id};
  const r=await rewrite(korean,configured,async()=>completion('{"replacement":"매일 사용하는 관리용 제품입니다"}'));
  assert.equal(r.mode,'live');assert.match(r.replacement,/매일/);
});
async function request(handler,method='POST',payload=body,headers={}) {
  const req=Readable.from([JSON.stringify(payload)]);Object.assign(req,{method,headers:{host:'localhost','content-type':'application/json',...headers},socket:{remoteAddress:'unit-test'}});
  const out={headers:{},status:0,body:null};
  const res={setHeader(k,v){out.headers[k]=v;},set statusCode(v){out.status=v;},end(v){out.body=JSON.parse(v);}};
  await handler(req,res);return out;
}
test('handler mode contains no secret, POST demo and methods',async()=>{
  const h=createHandler({env:{}});assert.deepEqual((await request(h,'GET')).body,{mode:'template'});
  assert.equal((await request(h)).body.mode,'template');assert.equal((await request(h,'DELETE')).status,405);
  assert.equal((await request(h,'POST',body,{'content-type':'text/plain'})).status,415);
  assert.equal((await request(h,'POST',body,{origin:'https://other.example'})).status,403);
  assert.equal((await request(h,'POST',body,{'content-length':'30000'})).status,413);
});
test('rate limit bounds paid requests and resets after one minute',async()=>{
  let time=0;const h=createHandler({env:{},now:()=>time});
  for(let i=0;i<10;i++)assert.equal((await request(h)).status,200);
  assert.equal((await request(h)).status,429);time=60001;assert.equal((await request(h)).status,200);
});
test('valid AI suggestion can reduce matches while capped score stays 100',async()=>{
  const text='cures acne. '.repeat(8);
  const r=await rewrite({text,findingId:analyze(text).findings[0].id},configured,async()=>completion('{"replacement":"supports everyday care"}'));
  assert.equal(r.mode,'live');
});
test('malformed origin fails safely',async()=>{
  assert.equal((await request(createHandler({env:{}}),'POST',body,{origin:'not-a-url'})).status,403);
});
