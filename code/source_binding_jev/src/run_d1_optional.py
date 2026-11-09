#!/usr/bin/env python3
"""Optional local d1 decision-model selector on *exactly* the frozen Jev questions.
Not an activation-steering study. Needs GPU and current Transformers; no fitting.
"""
import argparse,json,pathlib,os,sys
from core import canonical,digest,jsonl,verify,CANDIDATES
from execute import jev_payload,append

def main(args):
    _,_,selectors,_=verify(args.dir)
    out=pathlib.Path(args.dir)/'results';out.mkdir(exist_ok=True)
    dst=out/'d1_responses.jsonl'
    existing=list(jsonl(dst)) if dst.exists() else []
    seen={r['trial_id']:r for r in existing}
    if len(seen)!=len(existing):raise RuntimeError('Duplicate d1 response IDs')
    pending=[s for s in selectors if s['case_id'] not in seen]
    for s in selectors:
        if s['case_id'] in seen and seen[s['case_id']]['state_sha256']!=s['state_sha256']:
            raise RuntimeError('D1 state drift')
    print('Local d1 selector, pending',len(pending),'of',len(selectors))
    if not args.execute:print('DRY RUN, no GPU/model loading');return
    import torch
    from transformers import AutoModel
    if not torch.cuda.is_available():raise RuntimeError('d1 selector needs a GPU for this practical Colab run')
    model_id='LiquidAI/d1-3B'
    model=AutoModel.from_pretrained(model_id,trust_remote_code=True,dtype=torch.bfloat16).to('cuda').eval()
    if not hasattr(model,'system_one'):raise RuntimeError('This checkpoint does not expose system_one')
    for s in pending[:args.max_new] if args.max_new else pending:
        payload=jev_payload(s)
        result=model.system_one(payload['state'],payload['questions'])
        answers=result.get('answers',{})
        scores={}
        for name in CANDIDATES:
            value=answers[name]['noul']
            if not isinstance(value,(float,int)) or not 0<=value<=1:
                raise ValueError('Invalid d1 score, aborting: '+name)
            scores[name]=float(value)
        append(dst,{'trial_id':s['case_id'],'state_sha256':s['state_sha256'],
                    'model_id':model_id,'scores':scores,'raw':result})
    print('Saved d1 selector responses. No activation intervention performed.')

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--dir',default='runs/source_causal')
    p.add_argument('--execute',action='store_true');p.add_argument('--max-new',type=int)
    main(p.parse_args())
