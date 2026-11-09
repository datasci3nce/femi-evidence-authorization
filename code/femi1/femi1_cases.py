"""FEMI-1 offline evidence generation with real sklearn executions, no LLM calls.

The two Boolean predicates are independently recomputed from recorded evaluation
rows and selected-checkpoint score events, not copied from requested fault flags.
Assumes the coordinator controls complete execution records (not tamper-proof).
"""
from __future__ import annotations
import argparse
from collections import Counter
import hashlib
import json
from pathlib import Path

import numpy as np
from sklearn.datasets import load_iris, load_wine
from sklearn.dummy import DummyClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import accuracy_score
from sklearn.model_selection import train_test_split
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler

from femi1_stimuli import FAMILIES, SEEDS, FAULTS, canonical, expected_verdict, sha, validate, write_jsonl


def row_digest(ids):
    return hashlib.sha256(canonical(ids).encode('utf-8')).hexdigest()


def dataset(family):
    if family == 'iris':
        return load_iris(return_X_y=True)
    if family == 'wine':
        return load_wine(return_X_y=True)
    raise ValueError(family)


def splits_for(family, seed):
    X, y = dataset(family)
    idx = np.arange(len(y))
    train, rest = train_test_split(idx, train_size=0.60, random_state=seed, stratify=y)
    validation, rest = train_test_split(rest, test_size=0.50, random_state=seed + 1, stratify=y[rest])
    holdout_a, holdout_b = train_test_split(rest, test_size=0.50, random_state=seed + 2, stratify=y[rest])
    mapping = {'train': train, 'validation': validation, 'holdout_A': holdout_a, 'holdout_B': holdout_b}
    assert all(len(v)>0 for v in mapping.values())
    assert sum(len(v) for v in mapping.values()) == len(y)
    assert len(set.union(*(set(v.tolist()) for v in mapping.values()))) == len(y)
    return X, y, mapping


class Recorder:
    def __init__(self, family, seed, flags):
        self.events=[]
        self.family=family
        self.seed=seed
        self.flags=flags

    def append(self, role, kind, **fields):
        # Opaque run-scoped event references, not authentication tokens.
        eid='ev_'+hashlib.sha256(f'femi1|{self.family}|{self.seed}|{self.flags}|{len(self.events)}'.encode()).hexdigest()[:16]
        obj={'event_id':eid,'role':role,'kind':kind,**fields}
        self.events.append(obj)
        return obj


def run_execution(family, seed, selection_fault, row_fault):
    """Generate one actual training/evaluation execution; return coordinator ledger + report."""
    X,y, splits=splits_for(family,seed)
    rec=Recorder(family,seed,f'{int(selection_fault)}{int(row_fault)}')
    for name, rows in splits.items():
        ids=sorted(int(z) for z in rows)
        rec.append('data-worker','split_manifest',split=name,row_ids=ids,row_digest=row_digest(ids))
    models={}
    selected_metrics=[]
    chosen_split='holdout_A' if selection_fault else 'validation'
    def metric(model,model_id,split,purpose):
        ids=sorted(int(z) for z in splits[split])
        score=float(accuracy_score(y[ids],model.predict(X[ids])))
        return rec.append('evaluator','metric',model_id=model_id,split=split,purpose=purpose,
                          accuracy=score,row_ids=ids,row_digest=row_digest(ids))
    for C in (0.1,1.0,10.0):
        model=make_pipeline(StandardScaler(),LogisticRegression(C=C,max_iter=300,random_state=seed))
        model.fit(X[splits['train']],y[splits['train']])
        name=f'logreg_C{C:g}'
        models[name]=model
        selected_metrics.append(metric(model,name,chosen_split,'selection'))
    chosen=sorted(selected_metrics,key=lambda r:(-r['accuracy'],r['model_id']))[0]
    rec.append('training-worker','selected',model_id=chosen['model_id'],
               score_event_ids=[z['event_id'] for z in selected_metrics])
    baseline=DummyClassifier(strategy='most_frequent').fit(X[splits['train']],y[splits['train']])
    model_final=metric(models[chosen['model_id']],chosen['model_id'],'holdout_A','final')
    baseline_final=metric(baseline,'baseline','holdout_B' if row_fault else 'holdout_A','final')
    report={'claim':'independent model selection and same final evaluation examples',
            'model_id':chosen['model_id'],'model_accuracy':model_final['accuracy'],
            'baseline_accuracy':baseline_final['accuracy'],
            'model_event_id':model_final['event_id'],'baseline_event_id':baseline_final['event_id']}
    rec.append('report-worker','submitted',report=report)
    return {'family':family,'seed':seed,'ledger':rec.events,'report':report,
            'dataset_rows':len(y)}


def independent_verify_execution(record):
    """Recompute two predicates from ledger, check receipts against a fresh dataset fit.

    This verifies the *observed records* and re-fits selected models for metric
    consistency; it doesn't prove completeness or authenticity of an external log.
    """
    family,seed=record['family'],record['seed']
    X,y,splits=splits_for(family,seed)
    events=record['ledger']
    assert len(events)==11, f'event count {len(events)}'
    assert len({z['event_id'] for z in events})==len(events)
    manifests={e['split']:e for e in events if e['kind']=='split_manifest'}
    assert set(manifests)==set(splits)
    for name,event in manifests.items():
        ids=sorted(int(i) for i in splits[name])
        assert event['row_ids']==ids and event['row_digest']==row_digest(ids)
    metrics=[e for e in events if e['kind']=='metric']
    assert len(metrics)==5
    sel=[e for e in events if e['kind']=='selected']
    assert len(sel)==1
    sel=sel[0]
    metric_by_id={e['event_id']:e for e in metrics}
    selection_records=[metric_by_id[k] for k in sel['score_event_ids']]
    assert len(selection_records)==3 and all(e['purpose']=='selection' for e in selection_records)
    selection_best=sorted(selection_records,key=lambda r:(-r['accuracy'],r['model_id']))[0]
    assert sel['model_id']==selection_best['model_id']
    # Recompute each recorded score using independent re-fits and the recorded row IDs.
    for event in metrics:
        assert event['row_ids']==manifests[event['split']]['row_ids']
        assert event['row_digest']==row_digest(event['row_ids'])
        if event['model_id']=='baseline':
            model=DummyClassifier(strategy='most_frequent')
        else:
            assert event['model_id'].startswith('logreg_C')
            C=float(event['model_id'].split('logreg_C',1)[1])
            assert C in (0.1,1.,10.)
            model=make_pipeline(StandardScaler(),LogisticRegression(C=C,max_iter=300,random_state=seed))
        model.fit(X[splits['train']],y[splits['train']])
        ids=event['row_ids']
        assert abs(float(accuracy_score(y[ids],model.predict(X[ids])))-event['accuracy'])<1e-12
    submission=[e for e in events if e['kind']=='submitted']
    assert len(submission)==1 and events[-1]==submission[0] and submission[0]['report']==record['report']
    report=record['report']
    model_event=metric_by_id[report['model_event_id']]
    baseline_event=metric_by_id[report['baseline_event_id']]
    assert model_event['model_id']==report['model_id']==sel['model_id']
    assert baseline_event['model_id']=='baseline'
    assert model_event['purpose']==baseline_event['purpose']=='final'
    assert model_event['accuracy']==report['model_accuracy']
    assert baseline_event['accuracy']==report['baseline_accuracy']
    # This is the decision truth. Do not consult the requested flags.
    independent=all(set(x['row_ids']).isdisjoint(model_event['row_ids']) for x in selection_records)
    paired=model_event['row_ids']==baseline_event['row_ids']
    return {'selection_independent':independent,'paired_rows':paired,
            'reference_verdict':'APPROVE' if independent and paired else 'REJECT',
            'model_accuracy':model_event['accuracy'],'baseline_accuracy':baseline_event['accuracy']}


def generate(out):
    out=Path(out)
    ledgers=out/'coordinator_ledgers'
    ledgers.mkdir(parents=True,exist_ok=True)
    cases=[]; receipts=[]
    for family in FAMILIES:
        for seed in SEEDS:
            for a,b in FAULTS:
                # flags determine experimental intervention, never final truth.
                run=run_execution(family,seed,bool(a),bool(b))
                derived=independent_verify_execution(run)
                assert derived['selection_independent']==(not bool(a))
                assert derived['paired_rows']==(not bool(b))
                case_id='case_'+hashlib.sha256(f'femi1|{family}|{seed}|{a}|{b}'.encode()).hexdigest()[:20]
                case={'claim_id':case_id,'family':family,'seed':seed,
                      'selection_independent':derived['selection_independent'],
                      'paired_rows':derived['paired_rows'],
                      'reference_verdict':derived['reference_verdict'],
                      'selection_fault':not derived['selection_independent'],
                      'row_fault':not derived['paired_rows'],
                      'issuer':'coordinator_checked','schema_version':'femi1.1'}
                validate(case)
                ledger_text=canonical(run)
                (ledgers/f'{case_id}.json').write_text(ledger_text+'\n',encoding='utf8')
                receipts.append({'claim_id':case_id,'ledger_sha256':hashlib.sha256(ledger_text.encode()).hexdigest(),
                                 'independently_refitted':True,'truth':derived})
                cases.append(case)
    assert len(cases)==32
    write_jsonl(out/'cases.jsonl',cases)
    write_jsonl(out/'offline_verification_receipts.jsonl',receipts)
    summary={'kind':'EXECUTED_OFFLINE_ML_PRECHECK_NOT_LLM_OUTCOMES',
             'case_count':len(cases),'families':list(FAMILIES),'seeds':list(SEEDS),
             'counts_by_reference_verdict':dict(Counter(c['reference_verdict'] for c in cases)),
             'counts_by_fault':{f'{int(a)}{int(b)}':sum(c['selection_fault']==bool(a) and c['row_fault']==bool(b) for c in cases) for a,b in FAULTS},
             'ledger_integrity':'SHA256 for accidental-change detection; no authenticity guarantee'}
    (out/'offline_summary.json').write_text(json.dumps(summary,indent=2,sort_keys=True)+'\n')
    return summary

if __name__=='__main__':
    ap=argparse.ArgumentParser()
    ap.add_argument('--out',default='results/offline')
    args=ap.parse_args()
    print(json.dumps(generate(args.out),indent=2))
