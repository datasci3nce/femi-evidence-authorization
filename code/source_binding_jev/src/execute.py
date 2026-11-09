#!/usr/bin/env python3
"""Resumable frozen OpenRouter causal-auditor and Jev selector runner. No API calls without --execute."""
import argparse,json,os,pathlib,time,urllib.request,urllib.error
from core import canonical,digest,jsonl,verify,raw_verdict,CANDIDATES
AUDITOR_URL='https://openrouter.ai/api/v1/chat/completions'
JEV_URL='https://openrouter.ai/api/alpha/decisions'
AUDITOR={'model':'openai/gpt-oss-120b','provider':{'order':['Groq'],'allow_fallbacks':False},'temperature':0.2,'max_tokens':1600}
JEV_MODEL='typesafe/jev-1.14'

def append(path,row):
    with open(path,'a',encoding='utf8') as f:
        f.write(canonical(row)+'\n');f.flush();os.fsync(f.fileno())

def json_or_empty(path):return list(jsonl(path)) if path.exists() else []

def jev_payload(s):
    questions={}
    for name in CANDIDATES:
        questions[name]={
          'type':'noul',
          'instructions':('Relative to `baseline_auditor_request`, will making ONLY the edit described at '
                          f'`candidate_edits.{name}` change the GPT-OSS auditor final verdict on this case? '
                          'Predict what that model is likely to do, not what the correct verdict ought to be.'),
          'criteria':{'true':'The auditor changes its final APPROVE, REJECT, or DEFER verdict.',
                      'false':'The auditor retains exactly its prior final verdict.'},}
    return {'model':JEV_MODEL,'state':s['state'],'questions':questions}

def auditor_payload(t):return {**AUDITOR,'messages':t['messages']}

def http_json(url,payload,key):
    r=urllib.request.Request(url,data=canonical(payload).encode('utf8'),method='POST',
             headers={'Authorization':'Bearer '+key,'Content-Type':'application/json','HTTP-Referer':'https://colab.research.google.com'})
    try:
        with urllib.request.urlopen(r,timeout=150) as response:return json.load(response)
    except urllib.error.HTTPError as e:
        details=e.read().decode('utf8',errors='replace')[:1200]
        raise RuntimeError('HTTP '+str(e.code)+' '+details) from e

def validate_jev_response(result):
    answers=result['answers'];out={}
    for k in CANDIDATES:
        val=answers[k]['noul']
        if not isinstance(val,(int,float)) or not 0<=val<=1:raise ValueError('Invalid noul: '+k)
        out[k]=float(val)
    return out

def run(args):
    _,trials,selectors,_=verify(args.dir)
    path=pathlib.Path(args.dir)/'results';path.mkdir(exist_ok=True)
    is_jev=args.actor=='jev'
    candidates=selectors if is_jev else trials
    dest=path/('jev_responses.jsonl' if is_jev else 'auditor_responses.jsonl')
    prior=json_or_empty(dest)
    seen={r['trial_id'] for r in prior}
    if len(seen)!=len(prior):raise RuntimeError('Duplicate saved responses')
    todo=[];valid_ids=set()
    for r in candidates:
        key=r['case_id'] if is_jev else r['trial_id']
        valid_ids.add(key)
        payload=jev_payload(r) if is_jev else auditor_payload(r)
        request_hash=digest(canonical(payload))
        previous=next((x for x in prior if x['trial_id']==key),None)
        if previous:
            if previous['request_sha256']!=request_hash:raise RuntimeError('Existing response hash mismatch: '+key)
            if previous['model_id']!=(JEV_MODEL if is_jev else AUDITOR['model']):raise RuntimeError('Model mismatch: '+key)
        else:todo.append((key,payload,request_hash))
    if seen-valid_ids:raise RuntimeError('Unexpected IDs in response file')
    print('Actor:',args.actor,'total',len(candidates),'saved',len(prior),'remaining',len(todo))
    if not args.execute:
        print('DRY RUN: no network requests.');return
    key=os.environ.get('OPENROUTER_API_KEY')
    if not key:raise RuntimeError('Set OPENROUTER_API_KEY in Colab Secrets')
    conf={'actor':args.actor,'auditor':AUDITOR,'jev_model':JEV_MODEL,'version':1}
    config=path/'RUN_CONFIG.json'
    if config.exists() and json.loads(config.read_text())!=conf:raise RuntimeError('Runner config changed')
    if not config.exists():config.write_text(json.dumps(conf,indent=2)+'\n')
    if args.actor=='auditor' and not args.allow_auditor_before_selector:
        source=path/'jev_responses.jsonl'
        if not source.exists() or len(json_or_empty(source))!=len(selectors):
            raise RuntimeError('To keep selector predictions prospective, complete Jev first; use --allow-auditor-before-selector only as a documented protocol deviation')
    batch=todo[:args.max_new] if args.max_new else todo
    for idx,(trial_id,payload,reqhash) in enumerate(batch,1):
        start=time.monotonic()
        # Fail closed on HTTP/API problems; do not silently switch models or invent replies.
        obj=http_json(JEV_URL if is_jev else AUDITOR_URL,payload,key)
        if is_jev:
            scores=validate_jev_response(obj)
        else:
            if not isinstance(obj.get('choices'),list) or not obj['choices']:
                raise RuntimeError('Missing choices in auditor response; not saved: '+trial_id)
            served_provider=obj.get('provider')
            if served_provider and served_provider!='Groq':
                raise RuntimeError('Expected Groq provider, got '+str(served_provider))
            scores=None
        append(dest,{'trial_id':trial_id,'request_sha256':reqhash,
                     'model_id':JEV_MODEL if is_jev else AUDITOR['model'],
                     'served_model':obj.get('model'),'provider':obj.get('provider'),
                     'scores':scores,'raw':obj,'elapsed_s':round(time.monotonic()-start,3)})
        if idx%10==0:print('Saved',idx,'new',args.actor,'calls')
        time.sleep(args.pace)
    print('This batch saved:',len(batch),'of remaining:',len(todo))

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('actor',choices=('auditor','jev'))
    p.add_argument('--dir',default='runs/source_causal')
    p.add_argument('--execute',action='store_true')
    p.add_argument('--max-new',type=int)
    p.add_argument('--pace',type=float,default=0.8)
    p.add_argument('--allow-auditor-before-selector',action='store_true')
    a=p.parse_args();run(a)
