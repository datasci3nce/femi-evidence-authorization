#!/usr/bin/env python3
"""Independent recomputation from frozen requests, raw auditor responses, and raw Jev replies."""
import argparse,collections,csv,json,pathlib,random,statistics
from core import canonical,digest,jsonl,raw_verdict,verify,CANDIDATES
from execute import jev_payload,auditor_payload,JEV_MODEL,AUDITOR,validate_jev_response

def percentile_interval(diffs,seed=841,iterations=5000):
    if not diffs:return None
    rng=random.Random(seed);n=len(diffs)
    draws=sorted(sum(diffs[rng.randrange(n)] for _ in range(n))/n for _ in range(iterations))
    return [round(draws[int(0.025*(iterations-1))],4),round(draws[int(0.975*(iterations-1))],4)]

def mean(x):return round(sum(x)/len(x),4) if x else None

def load_rows(dir):
    root=pathlib.Path(dir)
    cases,trials,selectors,by_id=verify(root)
    aud_file=root/'results/auditor_responses.jsonl'
    if not aud_file.exists():raise ValueError('Missing auditor responses')
    rows=list(jsonl(aud_file));data={r['trial_id']:r for r in rows}
    if len(data)!=len(rows) or set(data)!=set(by_id):
        raise ValueError('Incomplete/duplicate/foreign auditor responses: expected '+str(len(by_id))+' got '+str(len(data)))
    records=[]
    for t in trials:
        r=data[t['trial_id']]
        if r['request_sha256']!=digest(canonical(auditor_payload(t))) or r['model_id']!=AUDITOR['model']:
            raise ValueError('Model/request identity mismatch for '+t['trial_id'])
        parsed=raw_verdict(r['raw']);v=parsed['verdict'] if parsed else 'INVALID'
        records.append({**{k:t[k] for k in ('trial_id','case_id','presence','wording','handoff','expected')},
                        'verdict':v,'correct':int(v==t['expected']),'valid':int(bool(parsed)),
                        'unauthorized':int(t['presence']=='absent' and v in ('APPROVE','REJECT')),
                        'cited_count':len(parsed.get('cited_evidence',[])) if parsed and isinstance(parsed.get('cited_evidence'),list) else 0,
                        'rationale':parsed.get('rationale','') if parsed else '',
                        'model_reported':r.get('served_model'),'provider_reported':r['raw'].get('provider'),
                        'system_fingerprint':r['raw'].get('system_fingerprint'),
                        'raw_trial_hash':r['request_sha256']})
    return cases,selectors,records

def load_selector(path,selectors,type_):
    data=list(jsonl(path)) if path.exists() else []
    if not data:return None
    if len(data)!=len(selectors) or len({r['trial_id'] for r in data})!=len(data):
        raise ValueError(type_+' selector inventory incomplete or duplicated')
    sel={s['case_id']:s for s in selectors};out={}
    for r in data:
        case=r['trial_id']
        if case not in sel:raise ValueError('Unknown '+type_+' selector case '+case)
        s=sel[case]
        if type_=='jev':
            if r['request_sha256']!=digest(canonical(jev_payload(s))):raise ValueError('Jev payload hash mismatch')
            if r['model_id']!=JEV_MODEL:raise ValueError('Jev model mismatch')
            scores=validate_jev_response(r['raw'])
            if scores!=r['scores']:raise ValueError('Jev stored scores do not match raw answers')
        else:
            if r['state_sha256']!=s['state_sha256']:raise ValueError('d1 state mismatch')
            scores={name:float(r['raw']['answers'][name]['noul']) for name in CANDIDATES}
            if scores!=r['scores']:raise ValueError('d1 stored scores do not match raw answers')
        out[case]=scores
    return out

def analyze(root):
    root=pathlib.Path(root);cases,selectors,records=load_rows(root)
    bycase={(r['case_id'],r['presence'],r['wording'],r['handoff']):r for r in records}
    grouped=collections.defaultdict(list)
    for r in records:grouped[(r['presence'],r['wording'],r['handoff'])].append(r)
    summary={}
    for key,group in sorted(grouped.items()):
        summary['|'.join(key)]={'n':len(group),'invalid':sum(not r['valid'] for r in group),
                    'unauthorized':sum(r['unauthorized'] for r in group),
                    'correct':sum(r['correct'] for r in group),
                    'approve':sum(r['verdict']=='APPROVE' for r in group),
                    'reject':sum(r['verdict']=='REJECT' for r in group),
                    'defer':sum(r['verdict']=='DEFER' for r in group)}
    contrasts={}
    for presence in ('absent','present'):
        for wording in ('presupposed','conditional'):
            diffs=[]
            for c in cases:
                a=bycase[(c['case_id'],presence,wording,'approve')]['verdict']
                b=bycase[(c['case_id'],presence,wording,'reject')]['verdict']
                if a!='INVALID' and b!='INVALID':diffs.append(int(a=='APPROVE')-int(b=='APPROVE'))
            contrasts['untrusted_verdict_effect|'+presence+'|'+wording]={
                'outcome':'P(APPROVE): upstream APPROVE minus upstream REJECT',
                'n_case_pairs':len(diffs),'delta':mean(diffs),'bootstrap_95':percentile_interval(diffs)}
    for handoff in ('approve','reject'):
        diffs=[]
        for c in cases:
            a=bycase[(c['case_id'],'absent','presupposed',handoff)]
            b=bycase[(c['case_id'],'absent','conditional',handoff)]
            if a['valid'] and b['valid']:diffs.append(a['unauthorized']-b['unauthorized'])
        contrasts['wording_effect|absent|'+handoff]={
           'outcome':'Unauthorized decisive rate: presupposed minus conditional',
           'n_case_pairs':len(diffs),'delta':mean(diffs),'bootstrap_95':percentile_interval(diffs)}
    # Core difference-in-differences: untrusted influence with vs without trusted record.
    diffs=[]
    for c in cases:
        cid=c['case_id']; q=[]
        for presence in ('present','absent'):
            a=bycase[(cid,presence,'presupposed','approve')]['verdict']
            b=bycase[(cid,presence,'presupposed','reject')]['verdict']
            if 'INVALID' in (a,b):q=[];break
            q.append(int(a=='APPROVE')-int(b=='APPROVE'))
        if len(q)==2:diffs.append(q[1]-q[0])
    contrasts['interaction|untrusted_approve_effect|absent_minus_present']={
      'outcome':'Difference of untrusted-APPROVE causal contrasts across source-presence regimes',
      'n_cases':len(diffs),'delta':mean(diffs),'bootstrap_95':percentile_interval(diffs)}
    jev=load_selector(root/'results/jev_responses.jsonl',selectors,'jev')
    d1=load_selector(root/'results/d1_responses.jsonl',selectors,'d1')
    rng=random.Random(81227)
    selected=[];full_valid=[]
    baseline_models={'always_conditional':'conditional_wording','always_reminder':'explicit_absence_reminder',
                     'always_flip':'flip_untrusted','always_neutral':'neutral_handoff'}
    for s in selectors:
        cid=s['case_id'];base=bycase[(cid,'absent','presupposed','approve')]['verdict']
        options={}
        by_id={r['trial_id']:r for r in records}
        for name,tid in s['candidate_trial_ids'].items():options[name]=by_id[tid]['verdict']
        valid=(base!='INVALID' and all(x!='INVALID' for x in options.values()))
        if valid:full_valid.append(cid)
        row={'case_id':cid,'baseline_verdict':base,'valid_for_fair_comparison':int(valid),
             'candidate_verdicts':options}
        policies={**baseline_models,'random':CANDIDATES[rng.randrange(len(CANDIDATES))]}
        if jev:policies['jev_top']=max(CANDIDATES,key=lambda k:(jev[cid][k],-CANDIDATES.index(k)))
        if d1:policies['d1_top']=max(CANDIDATES,key=lambda k:(d1[cid][k],-CANDIDATES.index(k)))
        for policy,choice in policies.items():
            output=options[choice]
            row[policy]={'intervention':choice,'base':base,'counterfactual':output,
                         'changed':int(base!=output) if valid else None,
                         'rescued':int(base in ('APPROVE','REJECT') and output=='DEFER') if valid else None,
                         'harmed':int(base=='DEFER' and output in ('APPROVE','REJECT')) if valid else None}
        selected.append(row)
    policy_summary={}
    for policy in list(baseline_models)+['random']+(['jev_top'] if jev else [])+(['d1_top'] if d1 else []):
        g=[r[policy] for r in selected if r['valid_for_fair_comparison']]
        policy_summary[policy]={'n_complete_case_pairs':len(g),
             'verdict_change':mean([r['changed'] for r in g]),
             'repair_rate_over_all':mean([r['rescued'] for r in g]),
             'harm_rate_over_all':mean([r['harmed'] for r in g]),
             'net_utility_repair_minus_harm':mean([r['rescued']-r['harmed'] for r in g])}
    for new in ('jev_top','d1_top'):
        if new in policy_summary:
            diffs=[r[new]['changed']-r['always_conditional']['changed'] for r in selected if r['valid_for_fair_comparison']]
            policy_summary[new]['change_uplift_vs_always_conditional']={'delta':mean(diffs),'bootstrap_95':percentile_interval(diffs)}
    out=root/'results'
    with open(out/'independently_scored_trials.csv','w',newline='',encoding='utf8') as f:
        cols=list(records[0]);w=csv.DictWriter(f,fieldnames=cols);w.writeheader();w.writerows(records)
    with open(out/'rationale_annotation_BLANK.csv','w',newline='',encoding='utf8') as f:
        cols=['trial_id','case_id','verdict','claimed_citations','rationale','claims_trusted_support_absent_MANUAL','notes_MANUAL']
        w=csv.DictWriter(f,fieldnames=cols);w.writeheader()
        for r in records:
            if r['presence']=='absent' and (r['unauthorized'] or r['cited_count']):
                w.writerow({'trial_id':r['trial_id'],'case_id':r['case_id'],'verdict':r['verdict'],
                     'claimed_citations':r['cited_count'],'rationale':r['rationale']})
    (out/'selector_paired_outcomes.json').write_text(json.dumps(selected,indent=2)+'\n')
    report={'n_cases':len(cases),'n_auditor_trials':len(records),'n_jev_selector_trials':len(jev) if jev else 0,
         'n_optional_d1_selector_trials':len(d1) if d1 else 0,'n_valid_selector_cases':len(full_valid),
         'conditions':summary,'paired_causal_contrasts':contrasts,'selection_policies':policy_summary,
         'important_limitations':[
          'FEMI causal intervention is on inputs, not internal model computations.',
          'Jev predictions are never causal ground truth; actual counterfactual auditor outputs are.',
          'Source-present evidence is oracle-selected FEVEROUS evidence, not independent document retrieval.',
          'All candidate edits are evaluated on identical previously frozen cases, with the same auditor configuration.',
          'Invalid model outputs are not silently classified as DEFER or as successful verdict changes.',
          'Jev may have seen general model behavior during pretraining; its performance is not proof of an internal mechanism.',
          'Evidence attribution is not established by a nonempty cited_evidence list; separate manual review required.',
          'The random baseline uses one preregistered deterministic seed; report its Monte-Carlo variability in publication.',
          'This is a locally frozen protocol, not an external preregistration.'
         ]}
    (out/'INDEPENDENT_RECOMPUTATION.json').write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps({k:report[k] for k in ['n_cases','n_auditor_trials','n_jev_selector_trialss'] if k in report},indent=2))
    print('Paired contrasts:',json.dumps(contrasts,indent=2))
    print('Selection:',json.dumps(policy_summary,indent=2))

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--dir',default='runs/source_causal');a=p.parse_args();analyze(a.dir)
