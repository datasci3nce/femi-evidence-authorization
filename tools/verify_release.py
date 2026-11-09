#!/usr/bin/env python3
"""Public-repository static checks only; not paid model replication."""
from pathlib import Path
import csv, json
R=Path(__file__).resolve().parent.parent
expected={
 'femi1/femi1_trial_scores.jsonl':480,
 'femi2/femi2_scored_trials.csv':144,
 'femi2r/trial_scores.csv':144,
 'femi3a/femi3a_scored_trials.csv':288,
 'femi4/trial_scores.csv':576,
 'contractnli/scored.csv':288,
 'feverous/scored.csv':288,
 'cross_model/scored.csv':864,
 'source_binding_jev/independently_scored_trials.csv':360,
}
fail=[]
for rel,n in expected.items():
 p=R/'results'/rel
 if not p.exists():fail.append(f'missing {rel}');continue
 if p.suffix=='.csv':
  with p.open(newline='',encoding='utf-8-sig') as f:rows=list(csv.DictReader(f))
 else:rows=[json.loads(x) for x in p.read_text(encoding='utf-8').splitlines() if x.strip()]
 if len(rows)!=n:fail.append(f'{rel}: {len(rows)} instead of {n}')
 else:print(f'OK {rel} ({n} rows)')
assert (R/'paper/FEMI_Final_Incident_Context.pdf').exists()
assert (R/'provenance/ORIGINAL_ARCHIVE_SHA256.json').exists()
if fail:raise SystemExit('RELEASE VALIDATION FAILED: '+'; '.join(fail))
print('RELEASE STRUCTURE CHECK PASSED (does not validate scientific correctness)')
