import csv,json,pathlib,subprocess,sys,tempfile,unittest,collections
ROOT=pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'src'))
from build_transfer import write_jsonl,stable,sha,read_jsonl

class EndToEndOffline(unittest.TestCase):
 def test_manifest_freeze_scorer_and_cross_model_no_http(self):
  with tempfile.TemporaryDirectory() as td:
   td=pathlib.Path(td); contracts=[]; labels={'h':{'hypothesis':'Proposition X'}}
   for i,ch in enumerate(['Entailment','Contradiction','NotMentioned']*2):
    contracts.append({'id':i,'text':'Example legal text with a provision '+str(i), 'spans':[[0,8]],
      'annotation_sets':[{'annotations':{'h':{'choice':ch,'spans':[0] if ch!='NotMentioned' else []}}}]})
   (td/'cnli.json').write_text(json.dumps({'documents':contracts,'labels':labels}))
   py=sys.executable;src=ROOT/'src'
   subprocess.run([py,str(src/'build_transfer.py'),'contract','--input',str(td/'cnli.json'),'--out',str(td/'cnli'),'--n','6'],check=True,capture_output=True)
   subprocess.run([py,str(src/'run_and_score.py'),'preflight','--dir',str(td/'cnli')],check=True,capture_output=True)
   # Create a synthetic RESPONSE INVENTORY only for pipeline testing; not research results.
   rows=list(read_jsonl(td/'cnli'/'manifest.jsonl'))
   results=td/'cnli'/'results';results.mkdir()
   write_jsonl(results/'responses.jsonl',[{'trial_id':sha(r['trial_id']+'|gpt_oss_120b_groq_anchor')[:24],
       'model_name':'gpt_oss_120b_groq_anchor','model_id':'openai/gpt-oss-120b',
       'parsed':{'verdict':r['expected_verdict'],'rationale':'OFFLINE-TEST ONLY','cited_evidence':[]},
       'result':{'provider':'TEST_ONLY','choices':[{'message':{'content':json.dumps({'verdict':r['expected_verdict'],'rationale':'OFFLINE-TEST ONLY','cited_evidence':[]})}}]}}
       for r in rows])
   subprocess.run([py,str(src/'run_and_score.py'),'analyze','--dir',str(td/'cnli'),
     '--models',str(ROOT/'models.anchor.json')],check=True,capture_output=True)
   report=json.loads((results/'analysis.json').read_text())
   self.assertEqual(report['n_trials'],36)
   self.assertEqual(report['summary']['cnli|gpt_oss_120b_groq_anchor|absent|conditional']['unsupported_decisive'],0)
   self.assertTrue((results/'scored.csv').exists())
   # Cross-model with a second fake bank of FEVEROUS-shaped cases for builder-only test.
   fever=td/'feverous';fever.mkdir();converted=[]
   for r in rows:
    q=dict(r);q['domain']='feverous';q['source_uid']='feverous:'+r['source_uid']
    converted.append(q)
   write_jsonl(fever/'manifest.jsonl',converted)
   import hashlib
   (fever/'FREEZE.json').write_text(json.dumps({'manifest_sha256':hashlib.sha256((fever/'manifest.jsonl').read_bytes()).hexdigest()}))
   subprocess.run([py,str(src/'build_cross_model.py'),'--contract-dir',str(td/'cnli'),
       '--feverous-dir',str(fever),'--out',str(td/'cross'),'--per-domain','3'],check=True,capture_output=True)
   subprocess.run([py,str(src/'run_and_score.py'),'preflight','--dir',str(td/'cross')],check=True,capture_output=True)
   self.assertEqual(len(list(read_jsonl(td/'cross'/'manifest.jsonl'))),36)

if __name__=='__main__': unittest.main()
