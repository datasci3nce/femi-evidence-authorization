#!/usr/bin/env python3
"""RAGTruth source-disjoint, task-balanced sample for local d1 eval. Zero model calls."""
from __future__ import annotations
import argparse, collections, hashlib, json, pathlib, random, statistics

TASKS=('QA','Summary','Data2txt')

def read_jsonl(file):
    with open(file,encoding='utf8') as f:
        for line in f:
            if line.strip(): yield json.loads(line)

def jsonl_bytes(rows):
    return (''.join(json.dumps(r,sort_keys=True,ensure_ascii=False,separators=(',',':'))+'\n' for r in rows)).encode('utf8')

def digest(b):return hashlib.sha256(b).hexdigest()

def file_sha(file):
    h=hashlib.sha256()
    with open(file,'rb') as f:
        for c in iter(lambda:f.read(1024*1024),b''):h.update(c)
    return h.hexdigest()

def item_text(x):
    return x if isinstance(x,str) else json.dumps(x,sort_keys=True,ensure_ascii=False,separators=(',',':'))

def make_state(source_info,response):
    return f'TRUSTED SOURCE MATERIAL:\n{item_text(source_info)}\n\nCANDIDATE RESPONSE TO AUDIT:\n{response}'

def build(respfile,srcfile,out,seed=1947,train_pairs_per_task=8,dev_per_task_per_label=10,test_per_task_per_label=20,max_chars=12000):
    out=pathlib.Path(out)
    if any(out.glob('d1_*')) or (out/'FREEZE.json').exists():raise FileExistsError('Frozen run exists. Use a fresh directory; do not overwrite it.')
    sources={str(v['source_id']):v for v in read_jsonl(srcfile)}
    if not sources:raise ValueError('Empty source info')
    bysplit=collections.defaultdict(lambda:collections.defaultdict(list))
    skipped=collections.Counter(); label_types=collections.Counter()
    for x in read_jsonl(respfile):
        split=x.get('split'); sid=str(x.get('source_id'))
        if split not in ('train','test') or sid not in sources:continue
        if x.get('quality','good') not in ('good',None,''):
            skipped['quality']+=1;continue
        s=sources[sid];task=s.get('task_type');
        if task not in TASKS:skipped['unknown_task']+=1;continue
        resp=x.get('response')
        if not isinstance(resp,str) or not resp.strip():skipped['empty']+=1;continue
        state=make_state(s['source_info'],resp)
        if len(state)>max_chars:skipped['too_long']+=1;continue
        labels=x.get('labels') or []
        if not isinstance(labels,list):skipped['bad_labels']+=1;continue
        if any(not isinstance(z,dict) for z in labels):skipped['bad_labels']+=1;continue
        for lab in labels:label_types[str(lab.get('label_type','unknown'))]+=1
        y=int(not labels)   # 1=NO annotated unsupported span; implicit_true still unsupported by SOURCE
        bysplit[split][sid].append({'id':str(x['id']),'source_id':sid,'task':task,'source_dataset':s.get('source'),
                        'original_split':split,'supported':y,'state':state,'n_spans':len(labels)})
    rng=random.Random(seed)
    train=[]; used_sources=set(); allocations={}
    for task in TASKS:
        eligible=[]
        for sid,rs in bysplit['train'].items():
            subset=[r for r in rs if r['task']==task]
            pos=[r for r in subset if r['supported']==1]
            neg=[r for r in subset if r['supported']==0]
            if pos and neg:eligible.append((sid,rng.choice(pos),rng.choice(neg)))
        rng.shuffle(eligible)
        if len(eligible)<train_pairs_per_task:
            raise ValueError(f'Only {len(eligible)} usable {task} training paired sources; need {train_pairs_per_task}')
        for sid,p,n in eligible[:train_pairs_per_task]:
            for r in (p,n):train.append(dict(r,partition='train'))
            used_sources.add(sid)
        allocations[task]={'train_paired_sources':train_pairs_per_task,'available_paired_sources':len(eligible)}
    # Dev from original train only and one row per distinct source, stratified per task/label
    dev=[]
    for task in TASKS:
        for y in (0,1):
            opts=[]
            for sid,rs in bysplit['train'].items():
                if sid in used_sources:continue
                ok=[r for r in rs if r['task']==task and r['supported']==y]
                if ok:opts.append((sid,rng.choice(ok)))
            rng.shuffle(opts)
            if len(opts)<dev_per_task_per_label:raise ValueError(f'{task} dev label {y}: only {len(opts)} sources')
            for sid,r in opts[:dev_per_task_per_label]:
                dev.append(dict(r,partition='dev'));used_sources.add(sid)
    # Test from RAGTruth's original test split only, one source per response.
    test=[]
    for task in TASKS:
        for y in (0,1):
            opts=[]
            for sid,rs in bysplit['test'].items():
                if sid in used_sources:continue
                ok=[r for r in rs if r['task']==task and r['supported']==y]
                if ok:opts.append((sid,rng.choice(ok)))
            rng.shuffle(opts)
            if len(opts)<test_per_task_per_label:raise ValueError(f'{task} test label {y}: only {len(opts)} distinct sources; need {test_per_task_per_label}')
            for sid,r in opts[:test_per_task_per_label]:
                test.append(dict(r,partition='test'));used_sources.add(sid)
    rows=train+dev+test
    if len(set((r['partition'],r['id']) for r in rows))!=len(rows):raise RuntimeError('Duplicate response IDs')
    if len({r['source_id'] for r in dev+test})!=len(dev+test):raise RuntimeError('Source leakage dev/test')
    if set(r['source_id'] for r in train)&set(r['source_id'] for r in dev+test):raise RuntimeError('Source leakage train/dev/test')
    out.mkdir(parents=True,exist_ok=False)
    b=jsonl_bytes(rows)
    (out/'d1_data_PRIVATE.jsonl').write_bytes(b)
    summary={'experiment':'D1-SOURCE-FAITHFULNESS-v2','status':'LOCALLY_FROZEN_NOT_PREREGISTERED',
     'seed':seed,'n_train':len(train),'n_dev':len(dev),'n_test':len(test),
     'allocation':{'train_pairs_per_task':train_pairs_per_task,'dev_per_task_per_label':dev_per_task_per_label,'test_per_task_per_label':test_per_task_per_label},
     'data_sha256':digest(b),'dataset_response_sha256':file_sha(respfile),'dataset_source_sha256':file_sha(srcfile),
     'per_partition_task_label':{p:dict(collections.Counter(f"{r['task']}|{r['supported']}" for r in rows if r['partition']==p)) for p in ('train','dev','test')},
     'skipped':dict(skipped),'raw_label_types':dict(label_types),
     'caveat':'Binary gold is presence/absence of RAGTruth annotated unsupported spans, not an exhaustive proof of source faithfulness. Labels and metadata are never sent to the model.'}
    (out/'FREEZE.json').write_text(json.dumps(summary,indent=2,ensure_ascii=False)+'\n')
    print(json.dumps(summary,indent=2))
    return summary

if __name__=='__main__':
    p=argparse.ArgumentParser()
    p.add_argument('--response-file',required=True);p.add_argument('--source-file',required=True);p.add_argument('--out',required=True)
    p.add_argument('--seed',type=int,default=1947);p.add_argument('--train-pairs-per-task',type=int,default=8)
    p.add_argument('--dev-per-task-per-label',type=int,default=10);p.add_argument('--test-per-task-per-label',type=int,default=20)
    p.add_argument('--max-chars',type=int,default=12000)
    a=p.parse_args();build(a.response_file,a.source_file,a.out,a.seed,a.train_pairs_per_task,a.dev_per_task_per_label,a.test_per_task_per_label,a.max_chars)
