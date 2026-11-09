import collections,hashlib,json,pathlib,sys,tempfile,unittest
ROOT=pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'src'))
from build_transfer import read_jsonl,stable,sha
from run_and_score import verify_manifest,expand,model_config,parse_decision
from build_cross_v2 import freeze

class CrossV2Tests(unittest.TestCase):
 @classmethod
 def setUpClass(cls):
    cls.run_dir=ROOT/'runs/cross_model'
    cls.rows=verify_manifest(cls.run_dir)
    cls.cases=list(read_jsonl(cls.run_dir/'cases_PRIVATE.jsonl'))
    cls.models=model_config(ROOT/'models.cross.v2.json')['models']
 def test_01_inventory_and_balance(self):
    self.assertEqual(len(self.rows),288)
    self.assertEqual(len(self.cases),48)
    self.assertEqual(len({x['case_id'] for x in self.cases}),48)
    self.assertEqual(collections.Counter(x['domain'] for x in self.cases),{'cnli':15,'feverous':33})
    self.assertEqual(collections.Counter((x['domain'],x['gold']) for x in self.cases),{
     ('cnli','Entailment'):5,('cnli','Contradiction'):5,('cnli','NotMentioned'):5,
     ('feverous','SUPPORTS'):11,('feverous','REFUTES'):11,('feverous','NOT ENOUGH INFO'):11})
 def test_02_unique_absent_prompts(self):
    rows=[x for x in self.rows if x['regime']=='absent']
    self.assertEqual(len(rows),96)
    self.assertEqual(len({stable(r['messages']) for r in rows}),96)
    cnli=[c for c in self.cases if c['domain']=='cnli']
    self.assertEqual(len({x['hypothesis_id'] for x in cnli}),15)
    self.assertEqual(len({x['claim'] for x in self.cases}),48)
 def test_03_evidence_and_pairing(self):
    by=collections.defaultdict(dict)
    for t in self.rows:
        msg=t['messages'];has=sum(m['content'].startswith('TRUSTED_EVIDENCE_RECORD:') for m in msg)
        self.assertEqual(has,1 if t['regime']=='present' else 0)
        self.assertEqual(sha(stable(msg)),t['request_sha256'])
        by[(t['case_id'],t['regime'])][t['wording']]=t
    self.assertEqual(len(by),144)
    for key,ds in by.items():
        self.assertEqual(set(ds),{'conditional','presupposed'})
        left=ds['conditional']['messages'];right=ds['presupposed']['messages']
        self.assertEqual(left[1:],right[1:])
        self.assertEqual(left[0]['content'].replace('If a trusted evidence record is provided below, use it to determine the verdict.','<W>'),
                         right[0]['content'].replace('Use the trusted evidence record below to determine the verdict.','<W>'))
 def test_04_expansion(self):
    x=expand(self.rows,self.models)
    self.assertEqual(len(x),864)
    self.assertEqual(len({t['trial_id'] for t in x}),864)
    self.assertEqual(collections.Counter(t['model_name'] for t in x),{m['name']:288 for m in self.models})
    for i in range(0,len(x),3):
        self.assertEqual([t['model_name'] for t in x[i:i+3]],[m['name'] for m in self.models])
 def test_05_build_determinism_and_no_overwrite(self):
    with tempfile.TemporaryDirectory() as d:
        target=pathlib.Path(d)/'runs'/'cross_model'
        fr=freeze(ROOT/'inputs/FEMI_TRANSFER_BOTH_RESULTS.zip',target)
        self.assertEqual(fr['manifest_sha256'],hashlib.sha256((self.run_dir/'manifest.jsonl').read_bytes()).hexdigest())
        self.assertEqual((target/'cases_PRIVATE.jsonl').read_bytes(),(self.run_dir/'cases_PRIVATE.jsonl').read_bytes())
        with self.assertRaises(RuntimeError):freeze(ROOT/'inputs/FEMI_TRANSFER_BOTH_RESULTS.zip',target)
 def test_06_parse(self):
    self.assertIsNone(parse_decision({'choices':[{'message':{'content':'DEFER'}}]}))
    self.assertEqual(parse_decision({'choices':[{'message':{'content':'{"verdict":"DEFER","rationale":"missing","cited_evidence":[]}'}}]})['verdict'],'DEFER')
    self.assertIsNone(parse_decision({'choices':[{'message':{'content':'{"verdict":"APPROVE", }'}}]}))
 def test_07_frozen_hash(self):
    fr=json.loads((self.run_dir/'FREEZE.json').read_text())
    self.assertEqual(fr['source_zip_sha256'],hashlib.sha256((ROOT/'inputs/FEMI_TRANSFER_BOTH_RESULTS.zip').read_bytes()).hexdigest())
    self.assertEqual(fr['n_planned_model_responses'],864)
    self.assertEqual(fr['cases_sha256'],hashlib.sha256((self.run_dir/'cases_PRIVATE.jsonl').read_bytes()).hexdigest())
 def test_08_table_modality_quota(self):
    v=[x for x in self.cases if x['domain']=='feverous']
    self.assertEqual(collections.Counter(c['metadata']['modality'] for c in v),{'table':21,'mixed':12})

if __name__=='__main__':unittest.main()
