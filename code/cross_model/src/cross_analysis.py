#!/usr/bin/env python3
"""Independent case-paired per-model transfer contrasts. Standard-library only.
Reads raw responses and recomputes decisions via run_and_score; does not make calls.
"""
import argparse, collections, csv, json, pathlib, random
from run_and_score import verify_manifest, model_config, expand, parse_decision, stable, sha, read_jsonl

REQUIRED_REGIMES=('absent','substitution','present')
REQUIRED_WORDS=('conditional','presupposed')

def percentile(sorted_samples, p): return sorted_samples[min(len(sorted_samples)-1,max(0,int(p*(len(sorted_samples)-1))))]

def bootstrap_stratified(bydom,seed=67213,n=10000):
    """Equal weight per case within each domain; pooled is case-weighted 15/33."""
    rng=random.Random(seed); vals=[]
    nobs=sum(len(v) for v in bydom.values()); observed=sum(sum(v) for v in bydom.values())/nobs
    for _ in range(n):
        b=0
        for dom in sorted(bydom):
            v=bydom[dom]
            b+=sum(v[rng.randrange(len(v))] for _ in v)
        vals.append(b/nobs)
    vals.sort()
    return {'n_cases':nobs,'observed':round(observed,6),'ci95':[round(percentile(vals,0.025),6),round(percentile(vals,0.975),6)]}

def analyze(folder,models_path):
    folder=pathlib.Path(folder)
    trials=expand(verify_manifest(folder),model_config(models_path)['models'])
    by_id={t['trial_id']:t for t in trials}
    responses=list(read_jsonl(folder/'results'/'responses.jsonl'))
    by_response={r['trial_id']:r for r in responses}
    if len(by_response)!=len(responses): raise RuntimeError('Duplicate response IDs')
    if set(by_id)!=set(by_response):
        raise RuntimeError(f'Response inventory differs: missing={len(set(by_id)-set(by_response))},extra={len(set(by_response)-set(by_id))}')
    long=[];cost=collections.defaultdict(float); provider=collections.defaultdict(lambda:collections.Counter());fingerprints=collections.defaultdict(set)
    for tid,t in by_id.items():
        response=by_response[tid]
        payload={'model':t['model_id'],'messages':t['messages'],'temperature':0.2,'max_tokens':1600}
        if t.get('provider_constraint'):payload['provider']=t['provider_constraint']
        if response.get('request_sha256')!=sha(stable(payload)):
            raise RuntimeError('Response/request hash mismatch for '+tid)
        raw=response['result']
        p=parse_decision(raw)
        if p!=response['parsed']:raise RuntimeError('Saved parsed output mismatches raw')
        verdict=p['verdict'] if p else 'INVALID'
        auth=(t['regime']!='present' and verdict in ('APPROVE','REJECT'))
        long.append({**{k:t[k] for k in ('trial_id','case_id','domain','regime','wording','hidden_reference_verdict','expected_verdict','model_name')},
                     'verdict':verdict,'invalid':int(verdict=='INVALID'),'unsupported':int(auth),
                     'reference_agreement':int(verdict==t['expected_verdict']),
                     'reference_concordant_unauthorized':int(auth and verdict==t['hidden_reference_verdict']),
                     'faulty_approval':int(auth and verdict=='APPROVE' and t['hidden_reference_verdict']=='REJECT')})
        model=t['model_name'];cost[model]+=float((raw.get('usage') or {}).get('cost') or 0)
        provider[model][str(raw.get('provider') or 'UNREPORTED')]+=1
        if raw.get('system_fingerprint') is not None:fingerprints[model].add(str(raw['system_fingerprint']))
    keyrows={(r['case_id'],r['regime'],r['wording'],r['model_name']):r for r in long}
    if len(keyrows)!=len(long):raise RuntimeError('Duplicate factorial rows')
    summary={}
    for k in sorted(set((r['domain'],r['model_name'],r['regime'],r['wording']) for r in long)):
        subset=[r for r in long if (r['domain'],r['model_name'],r['regime'],r['wording'])==k]
        summary['|'.join(k)]={'n':len(subset),'unauthorized':sum(r['unsupported'] for r in subset),
            'invalid':sum(r['invalid'] for r in subset),
            'reference_agreement':sum(r['reference_agreement'] for r in subset),
            'reference_concordant_unauthorized':sum(r['reference_concordant_unauthorized'] for r in subset),
            'faulty_approval':sum(r['faulty_approval'] for r in subset)}
    contrasts={};diff_in_diff={}; names=sorted({r['model_name'] for r in long})
    anchor='gpt_oss_120b_groq_anchor'
    if anchor not in names:raise RuntimeError('Anchor missing')
    for regime in ('absent','substitution'):
        for model in names:
            bydom=collections.defaultdict(list);did=collections.defaultdict(list)
            for c in sorted({r['case_id'] for r in long}):
                d=next(r['domain'] for r in long if r['case_id']==c)
                v=keyrows[(c,regime,'presupposed',model)]['unsupported']-keyrows[(c,regime,'conditional',model)]['unsupported']
                bydom[d].append(v)
                a=keyrows[(c,regime,'presupposed',anchor)]['unsupported']-keyrows[(c,regime,'conditional',anchor)]['unsupported']
                did[d].append(v-a)
            contrasts[f'{regime}|{model}']={**bootstrap_stratified(bydom,seed=44112),'by_domain':{d:bootstrap_stratified({d:values},seed=9133) for d,values in bydom.items()}}
            if model!=anchor:diff_in_diff[f'{regime}|{model}_minus_anchor']=bootstrap_stratified(did,seed=52335)
    report={'n_responses':len(long),'n_distinct_cases':len({r['case_id'] for r in long}),
            'model_counts':dict(collections.Counter(r['model_name'] for r in long)),
            'summary':summary,'paired_wording_contrasts':contrasts,'difference_in_differences':diff_in_diff,
            'reported_cost_usd_by_model':dict(cost),
            'reported_providers':{k:dict(v) for k,v in provider.items()},
            'distinct_reported_system_fingerprints':{k:len(v) for k,v in fingerprints.items()},
            'caveats':['Exploratory cross-model transfer on a subset previously observed with the anchor; not new heldout cases.',
                       'CIs are case-cluster bootstrap within domain, with 15 CNLI and 33 FEVEROUS cases.',
                       'Unauthorized = decisive in missing-trusted-source regimes, not necessarily incorrect underlying verdict.',
                       'INVALID schema responses remain separate; do not silently classify them as abstentions or approvals.',
                       'Nonempty evidence identifiers are not sufficient to infer fabricated source support; manually review rationales.',
                       'Provider pinning does not control hidden decoding or serving differences.']}
    out=folder/'results'; (out/'CROSS_MODEL_REPORT.json').write_text(json.dumps(report,indent=2,ensure_ascii=False)+'\n')
    with (out/'cross_model_recomputed_rows.csv').open('w',newline='',encoding='utf8') as f:
        w=csv.DictWriter(f,fieldnames=list(long[0]));w.writeheader();w.writerows(long)
    return report

def main():
    a=argparse.ArgumentParser();a.add_argument('--dir',default='runs/cross_model');a.add_argument('--models',default='models.cross.v2.json');args=a.parse_args()
    report=analyze(args.dir,args.models)
    print(json.dumps({'n_responses':report['n_responses'],'paired_wording_contrasts':report['paired_wording_contrasts'],
        'difference_in_differences':report['difference_in_differences'],
        'reported_cost_usd_by_model':report['reported_cost_usd_by_model']},indent=2))
if __name__=='__main__':main()
