"""Offline unit/integration tests use synthetic fixtures only; not research results."""
import csv,json,pathlib,sys,tempfile,unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'src'))
from core import canonical,digest,jsonl,verify,raw_verdict,condition_specs,CANDIDATES
from build import build
from execute import jev_payload,auditor_payload,validate_jev_response,append,AUDITOR,JEV_MODEL
from analyze import analyze

class Args:pass

class Tests(unittest.TestCase):
 def setUp(self):
    self.tmp=tempfile.TemporaryDirectory();p=Path(self.tmp.name)
    self.dir=p;self.out=p/'runs'/ 'new'
    self.wiki=p/'FeverousWikiv1';self.wiki.mkdir()
    labels=('SUPPORTS','REFUTES','NOT ENOUGH INFO')
    with (p/'dev.jsonl').open('w') as dev,(self.wiki/'wiki_001.jsonl').open('w') as wiki:
        for i in range(24):
            title='Test_page_'+str(i)
            rec={'id':str(i),'label':labels[i%3],'claim':'Claim about example '+str(i),
              'evidence':[{'content':[title+'_sentence_0'],'context':{}}]}
            dev.write(json.dumps(rec)+'\n')
            wiki.write(json.dumps({'title':title.replace('_',' '),'sentence_0':'Evidence value for '+str(i)})+'\n')
    (p/'excl.json').write_text(json.dumps({'ids':['0']}))
    a=Args();a.out=str(self.out);a.dev=str(p/'dev.jsonl');a.wiki=str(self.wiki)
    a.exclusions=str(p/'excl.json');a.seed=11;a.n=6;a.pool=6;a.min_table=0;a.max_chars=2000
    build(a)
 def tearDown(self):self.tmp.cleanup()
 def test_manifest_sizes_and_exclusion(self):
    c,t,s,_=verify(self.out)
    self.assertEqual((len(c),len(t),len(s)),(6,60,6))
    self.assertNotIn('feverous:0',{x['source_uid'] for x in c})
 def test_no_gold_or_trusted_source_leak_to_selector(self):
    c,t,s,_=verify(self.out)
    for selection in s:
        self.assertNotIn('gold',selection['state'])
        self.assertNotIn('trusted',selection['state'])
        self.assertEqual(set(selection['candidate_trial_ids']),set(CANDIDATES))
 def test_ten_conditions_per_case(self):
    c,t,s,_=verify(self.out)
    self.assertEqual(len(set((r['presence'],r['wording'],r['handoff']) for r in t)),10)
    self.assertEqual(sum(r['presence']=='present' for r in t),24)
 def test_absent_evidence_guaranteed(self):
    c,t,s,_=verify(self.out)
    for r in t:
        has=any(m['content'].startswith('TRUSTED_EVIDENCE_RECORD:\n') for m in r['messages'])
        self.assertEqual(has,r['presence']=='present')
        if not has:self.assertEqual(r['expected'],'DEFER')
 def test_resume_hash_and_tamper(self):
    p=self.out/'manifest.jsonl';data=p.read_text()
    p.write_text(data+'\n')
    with self.assertRaises((ValueError,AssertionError)):verify(self.out)
 def test_jev_questions(self):
    c,t,s,_=verify(self.out)
    payload=jev_payload(s[0]);self.assertEqual(payload['model'],JEV_MODEL)
    self.assertEqual(set(payload['questions']),set(CANDIDATES))
    self.assertIn('noul',payload['questions'][CANDIDATES[0]]['type'])
 def test_strict_raw_parse(self):
    self.assertIsNone(raw_verdict({'choices':[{'message':{'content':'{"verdict":"APPROVE",}'}}]}))
    self.assertEqual(raw_verdict({'choices':[{'message':{'content':'{"verdict":"DEFER"}'}}]})['verdict'],'DEFER')
 def test_jev_score_bounds(self):
    raw={'answers':{name:{'noul':0.5} for name in CANDIDATES}}
    self.assertEqual(len(validate_jev_response(raw)),4)
    raw['answers'][CANDIDATES[0]]['noul']=1.1
    with self.assertRaises(ValueError):validate_jev_response(raw)
 def test_end_to_end_synthetic_scoring(self):
    c,t,s,_=verify(self.out)
    dest=self.out/'results';dest.mkdir()
    for r in t:
        verdict=('APPROVE' if r['handoff'] in ('approve','reminder') else 'REJECT') if r['presence']=='absent' and r['wording']=='presupposed' else r['expected']
        raw={'choices':[{'message':{'content':json.dumps({'verdict':verdict,'rationale':'fixture','cited_evidence':[]})}}]}
        append(dest/'auditor_responses.jsonl',{'trial_id':r['trial_id'],'request_sha256':digest(canonical(auditor_payload(r))),
          'model_id':AUDITOR['model'],'raw':raw,'served_model':AUDITOR['model']})
    for row in s:
        raw={'model':JEV_MODEL,'answers':{name:{'noul':0.75 if name=='conditional_wording' else 0.25} for name in CANDIDATES}}
        append(dest/'jev_responses.jsonl',{'trial_id':row['case_id'],'request_sha256':digest(canonical(jev_payload(row))),
          'model_id':JEV_MODEL,'scores':validate_jev_response(raw),'raw':raw})
    analyze(str(self.out))
    report=json.loads((dest/'INDEPENDENT_RECOMPUTATION.json').read_text())
    self.assertEqual(report['n_auditor_trials'],60)
    self.assertEqual(report['n_jev_selector_trials'],6)
    self.assertEqual(report['n_valid_selector_cases'],6)
    self.assertEqual(report['selection_policies']['jev_top']['verdict_change'],1.0)
    self.assertIn('paired_causal_contrasts',report)
 def test_d1_optional_can_be_absent(self):
    self.assertFalse((self.out/'results'/'d1_responses.jsonl').exists())

if __name__=='__main__':unittest.main()
