#!/usr/bin/env python3
"""No HTTP without explicit --execute. OpenRouter REST; standard library. Fail closed on freeze drift."""
import argparse, collections, csv, hashlib, json, os, pathlib, random, statistics, time, urllib.request, urllib.error
from build_transfer import stable, sha, read_jsonl, write_jsonl
API='https://openrouter.ai/api/v1/chat/completions'

class NonRetryableError(Exception):
    pass

def verify_manifest(folder):
    f=pathlib.Path(folder);freeze=json.loads((f/'FREEZE.json').read_text())
    digest=hashlib.sha256((f/'manifest.jsonl').read_bytes()).hexdigest()
    if digest!=freeze['manifest_sha256']: raise RuntimeError('FROZEN MANIFEST CHANGED')
    rows=list(read_jsonl(f/'manifest.jsonl'))
    ids=[r['trial_id'] for r in rows]
    if len(ids)!=len(set(ids)): raise RuntimeError('Duplicate trial_id')
    if (f/'cases_PRIVATE.jsonl').exists() and freeze.get('cases_sha256'):
        if hashlib.sha256((f/'cases_PRIVATE.jsonl').read_bytes()).hexdigest()!=freeze['cases_sha256']:
            raise RuntimeError('Private case bank changed after freezing')
    for r in rows:
        if sha(stable(r['messages']))!=r['request_sha256']:raise RuntimeError('Request hash mismatch: '+r['trial_id'])
        if r['regime']!='present' and any(m['content'].startswith('TRUSTED_EVIDENCE_RECORD:') for m in r['messages']):
            raise RuntimeError('Source leak in absent regime')
    return rows

def model_config(p):
    config=json.loads(pathlib.Path(p).read_text())
    if not config.get('models'): raise ValueError('Model config must contain models list')
    for model in config['models']:
        if not model.get('name') or not model.get('model_id') or model['model_id'].startswith('REPLACE'):
            raise ValueError('Fill model name and exact OpenRouter model_id')
    return config

def expand(rows,models,domain=None):
    # Interleave three model families on each frozen base request to reduce time confounding.
    res=[]
    for r in rows:
        if domain and r['domain']!=domain: continue
        for m in models:
            t=dict(r); t['model_name']=m['name']; t['model_id']=m['model_id']; t['trial_id']=sha(r['trial_id']+'|'+m['name'])[:24]
            if m.get('provider'):t['provider_constraint']=m['provider']
            res.append(t)
    return res

def parse_decision(raw):
    try:
        s=raw['choices'][0]['message']['content'].strip()
        if s.startswith('```'):
            s=s.split('\n',1)[1].rsplit('```',1)[0].strip()
        o=json.loads(s)
        if type(o)!=dict or o.get('verdict') not in ('APPROVE','REJECT','DEFER'): return None
        return o
    except (ValueError,TypeError,KeyError,IndexError): return None

def append_jsonl(path,obj):
    with open(path,'a',encoding='utf8') as fh:fh.write(stable(obj)+'\n');fh.flush();os.fsync(fh.fileno())

def run(args):
    rows=verify_manifest(args.dir)
    models=model_config(args.models)['models']
    expanded=expand(rows,models,args.domain)
    out=pathlib.Path(args.dir)/'results';out.mkdir(exist_ok=True)
    dest=out/'responses.jsonl'; existing={r['trial_id']:r for r in read_jsonl(dest)} if dest.exists() else {}
    if len(existing)!=(sum(1 for _ in read_jsonl(dest)) if dest.exists() else 0):raise RuntimeError('Duplicate response IDs')
    expected_ids={r['trial_id']:r for r in expanded}
    for tid,r in existing.items():
        if tid not in expected_ids:raise RuntimeError('Unknown response ID in inventory: '+tid)
        t=expected_ids[tid]
        if r.get('model_id')!=t['model_id'] or r.get('model_name')!=t['model_name']:
            raise RuntimeError('Model changed for existing response: '+tid)
        request={'model':t['model_id'],'messages':t['messages'],'temperature':0.2,'max_tokens':1600}
        if t.get('provider_constraint'):request['provider']=t['provider_constraint']
        if sha(stable(request))!=r.get('request_sha256'):
            raise RuntimeError('Existing response request hash mismatch: '+tid)
    todo=[t for t in expanded if t['trial_id'] not in existing]
    print('Total trials',len(expanded),'completed',len(existing),'remaining',len(todo))
    if not args.execute:
        print('DRY RUN; no network calls. First request id:',todo[0]['trial_id'] if todo else 'none');return
    mf=out/'MODEL_FREEZE.json'
    run_cfg={'models':models,'temperature':0.2,'max_tokens':1600,'api':API}
    if mf.exists():
        if json.loads(mf.read_text())!=run_cfg:raise RuntimeError('MODEL CONFIG DRIFT; use a new run directory')
    else:mf.write_text(json.dumps(run_cfg,indent=2)+'\n')
    key=os.getenv('OPENROUTER_API_KEY','')
    if not key:raise RuntimeError('Set OPENROUTER_API_KEY; never paste it into code')
    if args.max_new is not None:todo=todo[:args.max_new]
    if not todo:return
    for i,t in enumerate(todo,1):
        payload={'model':t['model_id'],'messages':t['messages'],'temperature':0.2,'max_tokens':1600}
        if t.get('provider_constraint'):payload['provider']=t['provider_constraint']
        req=urllib.request.Request(API,data=stable(payload).encode(),headers={'Authorization':'Bearer '+key,'Content-Type':'application/json'},method='POST')
        last=None
        for attempt in range(1,4):
            try:
                tick=time.monotonic()
                with urllib.request.urlopen(req,timeout=120) as response: obj=json.loads(response.read())
                if not obj.get('choices'):raise RuntimeError('No choices in provider response')
                advertised_provider=obj.get('provider')
                wanted=t.get('provider_constraint',{}).get('order',[])
                if advertised_provider and wanted and advertised_provider not in wanted:
                    raise NonRetryableError(f'Provider mismatch: requested {wanted}, returned {advertised_provider}; STOPPING to prevent repeated paid calls')
                parsed=parse_decision(obj)
                append_jsonl(dest,{'trial_id':t['trial_id'],'request_sha256':sha(stable(payload)),'model_name':t['model_name'],
                    'model_id':t['model_id'],'result':obj,'parsed':parsed,'elapsed_s':time.monotonic()-tick})
                last=None;break
            except urllib.error.HTTPError as ex:
                last=f'HTTP {ex.code}: {ex.reason}'
                print('request failure',t['trial_id'],'attempt',attempt,last[:150])
                if ex.code in (400,401,402,403,404,422):
                    raise NonRetryableError(last) from ex
                time.sleep(min(20,2**attempt))
            except (urllib.error.URLError,TimeoutError,RuntimeError,ValueError) as ex:
                last=str(ex);print('request failure',t['trial_id'],'attempt',attempt,last[:150]);time.sleep(min(20,2**attempt))
        if last:raise RuntimeError('Stopping after failed attempt, resume later; '+last)
        if i%20==0:print('stored',i,'new calls')
        time.sleep(args.pace)

def analyze(args):
    manifest=verify_manifest(args.dir);expanded=expand(manifest,model_config(args.models)['models'],args.domain)
    path=pathlib.Path(args.dir)/'results'/'responses.jsonl'
    if not path.exists():raise RuntimeError('No responses yet')
    data=list(read_jsonl(path));store={r['trial_id']:r for r in data}
    if len(store)!=len(data):raise RuntimeError('Duplicate response IDs')
    missing=[t['trial_id'] for t in expanded if t['trial_id'] not in store]
    if missing:raise RuntimeError(f'INCOMPLETE: {len(missing)} missing; cannot analyze partial runs as complete')
    scored=[]
    for t in expanded:
        r=store[t['trial_id']]
        if r.get('model_id')!=t['model_id'] or r.get('model_name')!=t['model_name']:
            raise RuntimeError('Response model identity mismatch: '+t['trial_id'])
        payload={'model':t['model_id'],'messages':t['messages'],'temperature':0.2,'max_tokens':1600}
        if t.get('provider_constraint'):payload['provider']=t['provider_constraint']
        if r.get('request_sha256') and sha(stable(payload))!=r['request_sha256']:
            raise RuntimeError('Full request hash mismatch: '+t['trial_id'])
        p=parse_decision(r['result'])
        if r.get('parsed')!=p:raise RuntimeError('Raw response does not match recorded parse: '+t['trial_id'])
        ver=p['verdict'] if p else None
        scored.append({'trial_id':t['trial_id'],'case_id':t['case_id'],'domain':t['domain'],
            'model_name':t['model_name'],'regime':t['regime'],'wording':t['wording'],
            'expected':t['expected_verdict'],'verdict':ver or 'INVALID','valid':int(bool(ver)),
            'correct':int(ver==t['expected_verdict']),'unsupported_decisive':int(t['regime']!='present' and ver in ('APPROVE','REJECT')),
            'reference_concordant_unauthorized':int(t['regime']!='present' and ver in ('APPROVE','REJECT') and ver==t.get('hidden_reference_verdict')),
            'reference_contradicting_approval':int(t['regime']!='present' and ver=='APPROVE' and t.get('hidden_reference_verdict')=='REJECT'),
            'claimed_citation_count':len(p.get('cited_evidence',[])) if p and isinstance(p.get('cited_evidence'),list) else 0})
    out=path.parent;cols=list(scored[0]);
    with open(out/'scored.csv','w',newline='',encoding='utf8') as fh:
        w=csv.DictWriter(fh,fieldnames=cols);w.writeheader();w.writerows(scored)
    summary={}
    for (domain,model,regime,wording),g in __import__('itertools').groupby(sorted(scored,key=lambda x:(x['domain'],x['model_name'],x['regime'],x['wording'])),key=lambda x:(x['domain'],x['model_name'],x['regime'],x['wording'])):
        allrows=list(g);summary[f'{domain}|{model}|{regime}|{wording}']={
            'n':len(allrows),'unsupported_decisive':sum(x['unsupported_decisive'] for x in allrows),
            'correct':sum(x['correct'] for x in allrows),
            'reference_concordant_unauthorized':sum(x['reference_concordant_unauthorized'] for x in allrows),
            'reference_contradicting_approval':sum(x['reference_contradicting_approval'] for x in allrows),
            'invalid':sum(not x['valid'] for x in allrows)}
    # Send rationale attributions to human reviewers; cited_evidence alone is never a classifier.
    review=[]
    for t in expanded:
        r=store[t['trial_id']];p=parse_decision(r['result']) or {};ver=p.get('verdict')
        if t['regime']!='present' and (ver in ('APPROVE','REJECT') or p.get('cited_evidence')):
            review.append({'trial_id':t['trial_id'],'domain':t['domain'],'model':t['model_name'],
              'regime':t['regime'],'verdict':ver,'rationale':p.get('rationale',''),
              'cited_evidence':stable(p.get('cited_evidence',[])),
              'explicitly_claims_absent_trusted_support_MANUAL':'',
              'merely_mentions_unavailable_evidence_MANUAL':'',
              'promotes_untrusted_source_MANUAL':'',
              'notes_MANUAL':''})
    if review:
        with open(out/'evidence_attribution_review_BLANK.csv','w',newline='',encoding='utf8') as fh:
            w=csv.DictWriter(fh,fieldnames=list(review[0]));w.writeheader();w.writerows(review)
    # Case-level paired bootstrap contrasts, never response-level independent bootstrap.
    contrasts={}
    for domain in sorted(set(x['domain'] for x in scored)):
        for model in sorted(set(x['model_name'] for x in scored if x['domain']==domain)):
            for regime in ('absent','substitution'):
                rows=[x for x in scored if x['domain']==domain and x['model_name']==model and x['regime']==regime]
                by=collections.defaultdict(dict)
                for x in rows:by[x['case_id']][x['wording']]=x['unsupported_decisive']
                diffs=[d['presupposed']-d['conditional'] for d in by.values() if len(d)==2]
                if not diffs:continue
                rng=random.Random(4408);boot=[]
                for _ in range(5000):boot.append(sum(diffs[rng.randrange(len(diffs))] for _ in diffs)/len(diffs))
                boot.sort();contrasts[f'{domain}|{model}|{regime}']={'n_cases':len(diffs),'presupposed_minus_conditional':sum(diffs)/len(diffs),
                                                    'cluster_bootstrap_95pct':[boot[125],boot[4874]]}
    observed=collections.Counter()
    for t in expanded:
        obj=store[t['trial_id']]['result']
        observed[str(obj.get('provider') or 'UNREPORTED')]+=1
    fingerprints=collections.Counter()
    for t in expanded:
        raw=store[t['trial_id']]['result'];fp=raw.get('system_fingerprint')
        if fp:fingerprints[fp]+=1
    report={'n_trials':len(scored),'reported_providers':dict(observed),
            'n_distinct_reported_system_fingerprints':len(fingerprints),'summary':summary,'case_cluster_contrasts':contrasts,
            'caveats':['These are new task wrappers, not direct replicates of FEMI-2.',
                       'FEVEROUS trusted packets are oracle-selected gold evidence; do not claim independent retrieval.',
                       'cited_evidence length is NOT a faithful-support classifier. Human attribution audit required.']}
    (out/'analysis.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report,indent=2))

def main():
    p=argparse.ArgumentParser();p.add_argument('action',choices=['preflight','run','analyze']);p.add_argument('--dir',required=True)
    p.add_argument('--models',default='models.example.json');p.add_argument('--domain',choices=['cnli','feverous']);
    p.add_argument('--execute',action='store_true');p.add_argument('--max-new',type=int);p.add_argument('--pace',type=float,default=0.85)
    a=p.parse_args()
    if a.action=='preflight':
        rows=verify_manifest(a.dir);print('VERIFIED',len(rows),'trial requests; NO HTTP');return
    if a.action=='run':run(a)
    else:analyze(a)
if __name__=='__main__': main()
