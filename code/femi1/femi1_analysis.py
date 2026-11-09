"""Frozen FEMI-1 descriptive/cluster analysis. No API calls, no model outcomes generated.

Main preregistered contrasts: T2-T4, T3-T4 balanced correct-decisive
coverage, paired at eight (family,seed) base workflow clusters.
"""
from __future__ import annotations
import argparse,csv,hashlib,json,random
from collections import Counter,defaultdict
from pathlib import Path
from statistics import mean
from femi1_stimuli import canonical,load_jsonl,write_jsonl
from femi1_live import checks_manifest,trial_id,request_sha,json_verdict

PRIMARY=('T2','T3')
REPEATS=3
FAULTS=((False,False),(True,False),(False,True),(True,True))

def fault_name(sel,row):
    return f'sel{int(sel)}_row{int(row)}'

def index_run(manifest,results,strict_completed=True):
    expected={trial_id(z):z for z in manifest}
    assert len(expected)==len(manifest)
    obs={}
    for x in results:
        tid=x['trial_id']
        assert tid in expected, f'unknown trial_id {tid}'
        assert tid not in obs, f'duplicate response {tid}'
        assert x['request_sha256']==request_sha(expected[tid]), f'request hash mismatch: {tid}'
        obs[tid]=x
    missing=set(expected)-set(obs)
    if strict_completed and missing:
        raise ValueError(f'Live run incomplete: {len(missing)} trials missing. Do not analyze interim responses selectively.')
    return expected,obs,missing

def outcome(trial,received):
    if received is None:
        return {'category':'MISSING','correct_decisive':0,'parse_error':'no_response','valid_response':False}
    response=received.get('response')
    verdict,_,err=json_verdict(response) if isinstance(response,dict) and received.get('http_status')==200 else (None,None,'transport_failed')
    kind=verdict if verdict is not None else 'MALFORMED'
    truth=trial.get('reference_verdict',trial.get('expected_verdict'))
    return {'category':kind,'correct_decisive':int(kind==truth and kind in ('APPROVE','REJECT')),
            'wrong_approval':int(kind=='APPROVE' and truth=='REJECT'),
            'wrong_rejection':int(kind=='REJECT' and truth=='APPROVE'),
            'defer':int(kind=='DEFER'),'valid_response':verdict is not None,
            'parse_error':err}

def per_case_rates(main_manifest,observed):
    groups=defaultdict(list)
    trial_rows=[]
    for trial in main_manifest:
        tid=trial_id(trial)
        score=outcome(trial,observed.get(tid))
        row={k:trial[k] for k in ('case_id','family','seed','selection_fault','row_fault','reference_verdict','treatment','repeat')}
        row['trial_id']=tid;row.update(score)
        trial_rows.append(row)
        groups[(trial['family'],trial['seed'],trial['treatment'],trial['selection_fault'],trial['row_fault'])].append(score)
    for k,scores in groups.items():
        assert len(scores)==3, (k,len(scores))
    return groups,trial_rows

def base_balanced(groups, family, seed, treatment, valid_only=False):
    clean=[];invalid=[]
    for sel,row in FAULTS:
        scores=groups[(family,seed,treatment,sel,row)]
        if valid_only:
            scores=[x for x in scores if x['valid_response']]
            if not scores:return None
        v=mean(x['correct_decisive'] for x in scores)
        (invalid if (sel or row) else clean).append(v)
    return (clean[0]+mean(invalid))/2

def cluster_interval(values_by_base, base_keys, n=10000, seed=20261107):
    rng=random.Random(seed)
    samples=[]
    by_family={'iris':[x for x in base_keys if x[0]=='iris'], 'wine':[x for x in base_keys if x[0]=='wine']}
    for _ in range(n):
        sampled=[rng.choice(by_family[f]) for _ in range(4) for f in ('iris','wine')]
        samples.append(mean(values_by_base[k] for k in sampled))
    samples.sort()
    return [samples[int(0.025*n)],samples[int(0.975*n)]]

def summary(manifest,results,control_manifest,control_results):
    checks_manifest(manifest,480)
    checks_manifest(control_manifest,8,controls=True)
    _,observed,miss=index_run(manifest,results)
    _,control_obs,control_missing=index_run(control_manifest,control_results)
    groups,rows=per_case_rates(manifest,observed)
    keys=sorted(set((x['family'],x['seed']) for x in manifest))
    assert len(keys)==8
    estimated={}
    pair_rows=[]
    for family,seed in keys:
        per={t:base_balanced(groups,family,seed,t) for t in ('T0','T1','T2','T3','T4')}
        pair_rows.append({'family':family,'seed':seed,'balanced_correct_decisive':per,
                          'primary_T2_minus_T4':per['T2']-per['T4'],
                          'primary_T3_minus_T4':per['T3']-per['T4']})
    for t in PRIMARY:
        base_vals={(x['family'],x['seed']):x['balanced_correct_decisive'][t]-x['balanced_correct_decisive']['T4'] for x in pair_rows}
        estimated[f'{t}_minus_T4']={'point_estimate':mean(base_vals.values()),
                  'bootstrap_stratified_cluster_95pct':cluster_interval(base_vals,keys),
                  'individual_clusters':{f'{f}_{s}':v for (f,s),v in base_vals.items()},
                  'family_separated':{f:mean(base_vals[k] for k in keys if k[0]==f) for f in ('iris','wine')},
                  'bootstrap_replicates':10000}
    summaries=[]
    for t in ('T0','T1','T2','T3','T4'):
        for fault in (('clean',False,False),('selection_only',True,False),('row_only',False,True),('combined',True,True)):
            name,sel,row=fault
            sub=[x for x in rows if x['treatment']==t and x['selection_fault']==sel and x['row_fault']==row]
            counts=Counter(z['category'] for z in sub)
            assert len(sub)==24
            summaries.append({'treatment':t,'fault_condition':name,'planned':len(sub),
                      'decisions':{k:counts.get(k,0) for k in ('APPROVE','REJECT','DEFER','MALFORMED','MISSING')},
                      'correct_decisive':sum(x['correct_decisive'] for x in sub),
                      'false_approvals':sum(x.get('wrong_approval',0) for x in sub),
                      'false_rejections':sum(x.get('wrong_rejection',0) for x in sub),
                      'deferrals':sum(x.get('defer',0) for x in sub),
                      'response_valid_count':sum(x['valid_response'] for x in sub)})
    rates=[]
    for t in ('T0','T1','T2','T3','T4'):
        for stratum in ('clean','invalid'):
            sub=[x for x in rows if x['treatment']==t and ((not x['selection_fault'] and not x['row_fault'])==(stratum=='clean'))]
            n=len(sub)
            rates.append({'treatment':t,'stratum':stratum,'n_planned':n,'valid_responses':sum(x['valid_response'] for x in sub),
                          'correct_decisive_rate_ITT':sum(x['correct_decisive'] for x in sub)/n,
                          'false_approval_rate_ITT':sum(x.get('wrong_approval',0) for x in sub)/n,
                          'false_rejection_rate_ITT':sum(x.get('wrong_rejection',0) for x in sub)/n,
                          'deferral_rate_ITT':sum(x.get('defer',0) for x in sub)/n,
                          'malformed_or_missing_rate':sum(x['category'] in ('MALFORMED','MISSING') for x in sub)/n})
    valid_sensitivity={}
    for t in ('T0','T1','T2','T3','T4'):
        vals=[]
        for f,s in keys:
            v=base_balanced(groups,f,s,t,valid_only=True)
            if v is not None:vals.append(v)
        valid_sensitivity[t]={'complete_base_clusters':len(vals),'balanced_correct_rate_complete_clusters':mean(vals) if vals else None}
    controls=[{'trial_id':trial_id(z),**outcome(z,control_obs.get(trial_id(z)))} for z in control_manifest]
    sum_cost=0.;cost_n=0;total_in=0;total_out=0
    for z in list(observed.values())+list(control_obs.values()):
        u=z.get('usage')
        if not isinstance(u,dict):continue
        if isinstance(u.get('cost'),(int,float)):
            sum_cost+=float(u['cost']);cost_n+=1
        total_in+=u.get('prompt_tokens',0) if isinstance(u.get('prompt_tokens'),int) else 0
        total_out+=u.get('completion_tokens',0) if isinstance(u.get('completion_tokens'),int) else 0
    data={'study':'FEMI-1','status':'LIVE_RESPONSES_ANALYZED','planned_main':480,'observed_main':len(observed),
          'planned_controls':8,'observed_controls':len(control_obs),
          'base_clusters':8,'notes':['480 calls are not 480 independent samples','Reference verdict is explicitly supplied in the trusted record',
          'Cluster percentile intervals unstable with only four clusters per family','No significance tests or mechanism claims'],
          'primary_clustered_effects':estimated,'cluster_balance_rows':pair_rows,
          'by_treatment_and_fault':summaries,'by_treatment_and_stratum':rates,
          'response_valid_sensitivity':valid_sensitivity,
          'absent_evidence_controls':{'trials':controls,'deferred':sum(z['category']=='DEFER' for z in controls),
                  'unjustified_approval':sum(z['category']=='APPROVE' for z in controls)},
          'usage':{'api_reported_cost_sum_if_available':sum_cost if cost_n else None,
                  'num_cost_reported':cost_n,'prompt_tokens':total_in,'completion_tokens':total_out}}
    return data,rows

def blinded_rationale_sheet(manifest,results,output_csv,mapping_file):
    _,observed,_=index_run(manifest,results)
    rng=random.Random(20261107)
    rows=[];lookup=[]
    for z in manifest:
        resp=observed[trial_id(z)].get('response')
        parsed=None
        try:
            choices=resp.get('choices',[]) if isinstance(resp,dict) else []
            content=choices[0]['message']['content']
            parsed=json.loads(content) if isinstance(content,str) else None
        except (ValueError,KeyError,IndexError,TypeError):pass
        token=hashlib.sha256((trial_id(z)+'|femi1_mask_20261107').encode()).hexdigest()[:14]
        trusted=json.loads(z['request']['messages'][1]['content'].split('\n',1)[1])
        rows.append({'blind_id':token,'trusted_selection_independent':trusted['selection_independent'],
                     'trusted_paired_rows':trusted['paired_rows'],
                     'trusted_reference_verdict':trusted['reference_verdict'],
                     'model_verdict':parsed.get('verdict') if isinstance(parsed,dict) else '',
                     'rationale':parsed.get('rationale') if isinstance(parsed,dict) else '',
                     'cited_checks':canonical(parsed.get('cited_checks')) if isinstance(parsed,dict) else '',
                     'assessor_label':'','assessor_notes':''})
        lookup.append({'blind_id':token,'trial_id':trial_id(z),'treatment':z['treatment'],'family':z['family'],'seed':z['seed']})
    rng.shuffle(rows)
    with open(output_csv,'w',encoding='utf8',newline='') as f:
        writer=csv.DictWriter(f,fieldnames=list(rows[0]));writer.writeheader();writer.writerows(rows)
    write_jsonl(mapping_file,lookup)

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument('--manifest',required=True);ap.add_argument('--controls',required=True)
    ap.add_argument('--results',required=True);ap.add_argument('--control-results',required=True)
    ap.add_argument('--out',required=True)
    a=ap.parse_args()
    m=load_jsonl(a.manifest);c=load_jsonl(a.controls)
    r=load_jsonl(a.results) if Path(a.results).exists() else []
    cr=load_jsonl(a.control_results) if Path(a.control_results).exists() else []
    report,rows=summary(m,r,c,cr)
    out=Path(a.out);out.mkdir(parents=True,exist_ok=True)
    (out/'femi1_analysis.json').write_text(json.dumps(report,indent=2,sort_keys=True)+'\n')
    write_jsonl(out/'femi1_trial_scores.jsonl',rows)
    blinded_rationale_sheet(m,r,out/'blinded_rationale_coding.csv',out/'blind_mapping_KEEP_PRIVATE.jsonl')
    print('COMPLETE live FEMI-1 analysis saved at',out,'; primary contrasts:',report['primary_clustered_effects'])
if __name__=='__main__':main()
