#!/usr/bin/env python3
"""Freeze matched subset from BOTH previously generated transfer manifests; no API calls."""
import argparse,collections,hashlib,json,pathlib,random
from build_transfer import read_jsonl,write_jsonl,stable,sha
from run_and_score import verify_manifest

def main():
    p=argparse.ArgumentParser();p.add_argument('--contract-dir',required=True);p.add_argument('--feverous-dir',required=True)
    p.add_argument('--out',required=True);p.add_argument('--per-domain',type=int,default=24);p.add_argument('--seed',type=int,default=77004)
    a=p.parse_args();rng=random.Random(a.seed);out=pathlib.Path(a.out);out.mkdir(parents=True,exist_ok=True)
    if a.per_domain%3:raise ValueError('--per-domain must be divisible by 3 for gold-label balancing')
    merged=[];provenance={}
    for folder,domain in [(a.contract_dir,'cnli'),(a.feverous_dir,'feverous')]:
        inp=verify_manifest(folder);bycase=collections.defaultdict(list)
        for r in inp:
            assert r['domain']==domain
            bycase[r['case_id']].append(r)
        buckets=collections.defaultdict(list)
        for cid,rows in bycase.items():buckets[rows[0].get('hidden_reference_verdict','UNKNOWN')].append(cid)
        if set(buckets)!={'APPROVE','REJECT','DEFER'}:raise RuntimeError('Missing private reference labels in source bank')
        selected=[]
        for label in ('APPROVE','REJECT','DEFER'):
            ids=sorted(buckets[label]);rng.shuffle(ids)
            if domain=='feverous':
                def has_table(cid):
                    # Extract modality from TRUSTED_EVIDENCE_RECORD text; no gold verdict in prompt.
                    return any('_cell_' in m['content'] or '_table_caption_' in m['content']
                               for r in bycase[cid] if r['regime']=='present' for m in r['messages'] if m['content'].startswith('TRUSTED_EVIDENCE_RECORD:'))
                ids.sort(key=lambda cid:not has_table(cid))
            selected.extend(ids[:a.per_domain//3])
        if len(selected)!=a.per_domain:raise RuntimeError('Not enough balanced cases in '+domain)
        for cid in selected:
            if len(bycase[cid])!=6:raise RuntimeError('Incomplete 3×2 factorial on '+cid)
            for orig in bycase[cid]:
                t=dict(orig);t['case_id']=domain+'-'+orig['case_id']
                t['trial_id']=sha(domain+'|'+orig['trial_id'])[:18]
                merged.append(t)
        provenance[domain]={'source_manifest_sha256':json.loads((pathlib.Path(folder)/'FREEZE.json').read_text())['manifest_sha256'],
                            'selected_n_distinct':a.per_domain,'selected_reference_verdict_counts':dict(collections.Counter(bycase[cid][0]['hidden_reference_verdict'] for cid in selected))}
    rng.shuffle(merged);write_jsonl(out/'manifest.jsonl',merged)
    freeze={'experiment':'FEMI-CROSS-MODEL-1','seed':a.seed,'manifest_sha256':hashlib.sha256((out/'manifest.jsonl').read_bytes()).hexdigest(),
            'n_trials_per_model':len(merged),'n_models_intended':3,'provenance':provenance,
            'note':'Re-run anchor contemporaneously. Case IDs are joined only within each domain.'}
    (out/'FREEZE.json').write_text(json.dumps(freeze,indent=2)+'\n');print(json.dumps(freeze,indent=2))
if __name__=='__main__':main()
