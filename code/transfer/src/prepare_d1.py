#!/usr/bin/env python3
"""Build source-disjoint RAGTruth d1 binary source-faithfulness evaluation. No model calls."""
import argparse,collections,hashlib,json,pathlib,random
from build_transfer import stable,sha,read_jsonl,write_jsonl

def create(response_file,source_file,outdir,seed,n_train_pairs,n_dev,n_test,max_chars):
    source={str(x['source_id']):x for x in read_jsonl(source_file)}
    candidates={'train':collections.defaultdict(list),'test':collections.defaultdict(list)}
    skipped=collections.Counter()
    for item in read_jsonl(response_file):
        if item.get('split') not in candidates or str(item.get('source_id')) not in source:continue
        if item.get('quality','good') not in ('good',None,''):skipped['quality']+=1;continue
        ref=source[str(item['source_id'])]
        body=stable(ref.get('source_info'))
        if len(body)+len(item.get('response',''))>max_chars: skipped['long']+=1;continue
        labels=item.get('labels') or []
        # RAGTruth annotations concern source-faithfulness, not public-world truth.
        y=int(len(labels)==0)
        state=('SOURCE_DOCUMENT:\n'+body+'\n\nCANDIDATE_RESPONSE:\n'+item.get('response',''))
        case={'source_uid':str(item['source_id']),'response_id':str(item['id']),
              'state':state,'supported':y,'task_type':ref.get('task_type','unspecified'),
              'original_split':item['split'],'n_annotated_spans':len(labels)}
        candidates[item['split']][case['source_uid']].append(case)
    rng=random.Random(seed)
    # Training needs pairs with SAME SOURCE but opposite annotation labels.
    usable=[]
    for sid,rs in candidates['train'].items():
        pos=[x for x in rs if x['supported']==1]; neg=[x for x in rs if x['supported']==0]
        if pos and neg:usable.append((sid,rng.choice(pos),rng.choice(neg)))
    rng.shuffle(usable)
    if len(usable)<n_train_pairs:raise RuntimeError(f'Only {len(usable)} contrastive sources, need {n_train_pairs}')
    train=[];used=set()
    for sid,p,n in usable[:n_train_pairs]:
        train.extend([dict(p,split='train'),dict(n,split='train')]);used.add(sid)
    remaining=[(sid,rs) for sid,rs in candidates['train'].items() if sid not in used]
    rng.shuffle(remaining)
    dev=[]
    for sid,rs in remaining:
        want=int(len(dev)%2==0)
        available=[x for x in rs if x['supported']==want]
        if available:dev.append(dict(rng.choice(available),split='dev'));used.add(sid)
        if len(dev)==n_dev:break
    if len(dev)!=n_dev:raise RuntimeError(f'Need {n_dev} dev distinct sources; got {len(dev)}')
    options=list(candidates['test'].items());rng.shuffle(options)
    test=[];test_sources=set()
    for sid,rs in options:
        want=int(len(test)%2==0)
        avail=[x for x in rs if x['supported']==want]
        if avail and sid not in test_sources:
            test.append(dict(rng.choice(avail),split='test'));test_sources.add(sid)
        if len(test)==n_test:break
    if len(test)!=n_test:raise RuntimeError(f'Need {n_test} balanced test sources; got {len(test)}')
    assert not (used&test_sources)
    data=train+dev+test
    out=pathlib.Path(outdir);out.mkdir(parents=True,exist_ok=True)
    write_jsonl(out/'d1_data_PRIVATE.jsonl',data)
    summary={'experiment':'D1-RAGTruth-1','seed':seed,'train_pairs':n_train_pairs,'dev_source_count':len(dev),
             'test_source_count':len(test),'balanced_test':dict(collections.Counter(x['supported'] for x in test)),
             'response_sha256':hashlib.sha256(pathlib.Path(response_file).read_bytes()).hexdigest(),
             'source_sha256':hashlib.sha256(pathlib.Path(source_file).read_bytes()).hexdigest(),
             'data_sha256':hashlib.sha256((out/'d1_data_PRIVATE.jsonl').read_bytes()).hexdigest(),
             'skipped':dict(skipped),'warning':'Annotation-based binary corpus label. Human review required for nuanced attribution.'}
    (out/'FREEZE.json').write_text(json.dumps(summary,indent=2)+'\n');print(json.dumps(summary,indent=2))

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--response-file',required=True);p.add_argument('--source-file',required=True)
    p.add_argument('--out',required=True);p.add_argument('--seed',type=int,default=125);p.add_argument('--train-pairs',type=int,default=24)
    p.add_argument('--dev',type=int,default=40);p.add_argument('--test',type=int,default=100);p.add_argument('--max-chars',type=int,default=16000)
    a=p.parse_args();create(a.response_file,a.source_file,a.out,a.seed,a.train_pairs,a.dev,a.test,a.max_chars)
