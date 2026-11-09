#!/usr/bin/env python3
"""Freeze a cross-family matched subset from both completed transfer archives.
NO model calls. Input ZIP contains cnli/ and feverous/ case bank and frozen manifest.
The selected prompts are byte-identical to their transfer parent per case/regime/wording.
"""
import argparse, collections, hashlib, itertools, json, pathlib, random, zipfile
from build_transfer import stable, sha, write_jsonl
from run_and_score import verify_manifest

LABELS=('APPROVE','REJECT','DEFER')
SEED=81324

def files_to_dir(srczip,out):
    """Extract only original frozen case banks and manifest; guard against ZIP traversal."""
    out.mkdir(parents=True,exist_ok=True)
    with zipfile.ZipFile(srczip) as z:
        for domain in ('cnli','feverous'):
            for name in ('cases_PRIVATE.jsonl','manifest.jsonl','FREEZE.json'):
                member=f'{domain}/{name}'
                if member not in z.namelist(): raise RuntimeError('Missing archive member: '+member)
                d=out/domain; d.mkdir(parents=True,exist_ok=True)
                (d/name).write_bytes(z.read(member))

def load(source,domain):
    folder=source/domain
    trials=verify_manifest(folder)
    cases=[json.loads(l) for l in (folder/'cases_PRIVATE.jsonl').read_text().splitlines() if l.strip()]
    freeze=json.loads((folder/'FREEZE.json').read_text())
    bycase=collections.defaultdict(list)
    for t in trials:
        if t['domain']!=domain:raise RuntimeError('Incorrect domain in input')
        bycase[t['case_id']].append(t)
    if len(bycase)!=len(cases):raise RuntimeError('Case / manifest cardinality differs')
    for c in cases:
        rows=bycase[c['case_id']]
        if len(rows)!=6 or set((r['regime'],r['wording']) for r in rows)!={
            (r,w) for r in ('absent','substitution','present') for w in ('conditional','presupposed')}:
            raise RuntimeError('Incomplete factorial: '+domain+':'+c['case_id'])
        if len({r['hidden_reference_verdict'] for r in rows})!=1:
            raise RuntimeError('Inconsistent private label')
    return cases,bycase,freeze

def pick_contract(cases,bycase,rng):
    """Exactly five cases per label, with no repeated hypothesis across labels."""
    grouped={lbl:collections.defaultdict(list) for lbl in LABELS}
    for c in cases:
        lbl=bycase[c['case_id']][0]['hidden_reference_verdict']
        if lbl not in grouped: raise RuntimeError('Unexpected reference label')
        grouped[lbl][c['hypothesis_id']].append(c)
    # Enumerate choices of hypothesis IDs and pick a seeded feasible combination.
    cands={lbl:list(itertools.combinations(sorted(grouped[lbl]),5)) for lbl in LABELS}
    solutions=[]
    for reject in cands['REJECT']:
        rejset=set(reject)
        for approve in cands['APPROVE']:
            aset=set(approve)
            if rejset&aset:continue
            for defer in cands['DEFER']:
                ds=set(defer)
                if (ds&aset) or (ds&rejset):continue
                solutions.append({'APPROVE':approve,'REJECT':reject,'DEFER':defer})
    if not solutions:raise RuntimeError('Cannot select 15 globally unique hypotheses balanced 5/5/5')
    chosen=rng.choice(solutions)
    selected=[]
    for lbl in LABELS:
        for hid in chosen[lbl]:
            selected.append(rng.choice(sorted(grouped[lbl][hid],key=lambda x:x['case_id'])))
    if len(set(c['claim'] for c in selected))!=15:raise RuntimeError('Duplicate absent-record claim after selection')
    return selected,{'n_feasible_assignments':len(solutions),'hypotheses_by_label':{k:list(v) for k,v in chosen.items()}}

def pick_feverous(cases,bycase,rng):
    # Exact 11/11/11 label balance, 21 table + 12 mixed cases; achieved with quotas below.
    quotas={
        'APPROVE':{'table':6,'mixed':5},
        'REJECT':{'table':9,'mixed':2},
        'DEFER':{'table':6,'mixed':5}
    }
    buckets=collections.defaultdict(list)
    for c in cases:
        lbl=bycase[c['case_id']][0]['hidden_reference_verdict']
        buckets[(lbl,c['metadata']['modality'])].append(c)
    selected=[]
    for lbl in LABELS:
        for modality,n in quotas[lbl].items():
            options=sorted(buckets[(lbl,modality)],key=lambda x:x['case_id']);rng.shuffle(options)
            if len(options)<n:raise RuntimeError(f'Insufficient {lbl} {modality}: {len(options)} < {n}')
            selected.extend(options[:n])
    if len({c['claim'] for c in selected})!=33:raise RuntimeError('FEVEROUS repeated claim')
    return selected,quotas

def freeze(source_zip,out,seed=SEED):
    out=pathlib.Path(out)
    if (out/'results'/'responses.jsonl').exists():
        raise RuntimeError('LIVE RESPONSES EXIST: refusing to overwrite an executed run')
    if (out/'FREEZE.json').exists() or (out/'manifest.jsonl').exists():
        raise RuntimeError('FROZEN MANIFEST EXISTS: use preflight instead of rebuilding')
    rng=random.Random(seed)
    src=out.parent/'.source_inputs'
    files_to_dir(source_zip,src)
    selected=[];details={}
    for dom,picker in [('cnli',pick_contract),('feverous',pick_feverous)]:
        cases,bycase,fr=load(src,dom)
        pick,info=picker(cases,bycase,rng)
        details[dom]={'selected':len(pick),'labels':dict(collections.Counter(bycase[c['case_id']][0]['hidden_reference_verdict'] for c in pick)),
            'selected_case_ids':[c['case_id'] for c in pick],
            'original_manifest_sha256':fr['manifest_sha256'],'selection':info}
        for c in pick: selected.append((dom,c,bycase[c['case_id']]))
    if len(selected)!=48:raise RuntimeError('Not 48 cases')
    records=[];bank=[]
    for dom,c,rows in selected:
        newcase=f'{dom}--{c["case_id"]}'
        cc={**c,'case_id':newcase,'domain':dom,'original_case_id':c['case_id']}
        bank.append(cc)
        for orig in rows:
            t={**orig,'case_id':newcase,'source_trial_id':orig['trial_id']}
            # New stable trial IDs; source request_sha256 unchanged and independently validated.
            t['trial_id']=sha('cross-v2|'+dom+'|'+orig['trial_id'])[:24]
            records.append(t)
    rng.shuffle(records);rng.shuffle(bank)
    if len(records)!=288 or len({x['trial_id'] for x in records})!=288:
        raise RuntimeError('Expected 288 unique base trials')
    # Each pair is a literal system-sentence change, and source authority is absent outside present.
    all_prompts=set(); paired=collections.defaultdict(dict)
    for t in records:
        msgs=t['messages']
        if sha(stable(msgs))!=t['request_sha256']:raise RuntimeError('Source prompt was changed')
        trusted=[m for m in msgs if m['content'].startswith('TRUSTED_EVIDENCE_RECORD:')]
        if (len(trusted)==1)!=(t['regime']=='present'):
            raise RuntimeError('Source presence mismatch')
        if t['regime']=='absent':
            canonical=stable(msgs)
            if canonical in all_prompts:raise RuntimeError('Duplicate absent-record literal prompt')
            all_prompts.add(canonical)
        paired[(t['case_id'],t['regime'])][t['wording']]=msgs
    for key,x in paired.items():
        if set(x)!={'presupposed','conditional'}:raise RuntimeError('Unpaired cell')
        a=x['presupposed'];b=x['conditional']
        if len(a)!=len(b):raise RuntimeError('Wording affects message count')
        if a[0]['role']!='system' or b[0]['role']!='system':raise RuntimeError('Expected system instruction')
        def prefix(s):
            return s.replace('Use the trusted evidence record below to determine the verdict.', '<WORDING>')\
                    .replace('If a trusted evidence record is provided below, use it to determine the verdict.','<WORDING>')
        if prefix(a[0]['content'])!=prefix(b[0]['content']) or a[1:]!=b[1:]:
            raise RuntimeError('More than the declared wording differs: '+str(key))
    out.mkdir(parents=True,exist_ok=True)
    write_jsonl(out/'manifest.jsonl',records)
    write_jsonl(out/'cases_PRIVATE.jsonl',bank)
    fr={'experiment':'FEMI-CROSS-MODEL-1-v2','seed':seed,'source_zip_sha256':hashlib.sha256(pathlib.Path(source_zip).read_bytes()).hexdigest(),
        'n_unique_cases':48,'n_base_trials':288,'n_models':3,'n_planned_model_responses':864,
        'selected_by_domain':details,
        'manifest_sha256':hashlib.sha256((out/'manifest.jsonl').read_bytes()).hexdigest(),
        'cases_sha256':hashlib.sha256((out/'cases_PRIVATE.jsonl').read_bytes()).hexdigest(),
        'research_limitations':['Same cases and prompt family previously evaluated on the anchor; NOT new held-out cases.',
          'FEVEROUS uses oracle-selected reference evidence; no independent retrieval.',
          'Reference-label agreement with present trusted evidence is not independently audited truth.',
          'Cross-model contrasts can be affected by differences in serving backend and reasoning defaults.']}
    (out/'FREEZE.json').write_text(json.dumps(fr,indent=2,ensure_ascii=False)+'\n')
    print(json.dumps({'built':str(out),'cases':48,'base_requests':len(records),'model_responses':864,
                      'case_labels':dict(collections.Counter(x['gold'] for x in bank)),
                      'source_sha256':fr['source_zip_sha256'],'manifest_sha256':fr['manifest_sha256'],
                      'case_counts':{d:det['labels'] for d,det in details.items()}},indent=2))
    return fr

def main():
    p=argparse.ArgumentParser();p.add_argument('--source-zip',required=True);p.add_argument('--out',required=True)
    p.add_argument('--seed',type=int,default=SEED);args=p.parse_args()
    freeze(args.source_zip,args.out,args.seed)
if __name__=='__main__':main()
