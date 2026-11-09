import csv,hashlib,json,pathlib,sys,tempfile,unittest
ROOT=pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'src'))
from build_transfer import contract_candidates,feverous_candidates,select_balanced,make_manifest,write_jsonl,sha,stable,page_element
from prepare_d1 import create
from run_and_score import parse_decision, verify_manifest

class PacketTests(unittest.TestCase):
 def test_contract_and_no_gold_leak(self):
  with tempfile.TemporaryDirectory() as td:
   path=pathlib.Path(td)/'contract.json'
   labels={'h':{'hypothesis':'Every agreement requires notification.'}}
   docs=[]
   for i,ch in enumerate(['Entailment','Contradiction','NotMentioned']*2):
    doc={'id':i,'text':'This is the authoritative document and it is not an annotation label.',
         'spans':[[0,10]],'annotation_sets':[{'annotations':{'h':{'choice':ch,'spans':[0] if ch!='NotMentioned' else []}}}]}
    docs.append(doc)
   path.write_text(json.dumps({'documents':docs,'labels':labels}))
   cs,reject=contract_candidates(path,1000);got=select_balanced(cs,6,8);manifest=make_manifest(got,8)
   self.assertEqual(len(manifest),36)
   self.assertEqual(sum(r['expected_verdict']=='DEFER' for r in manifest),28) # absent+sub + 2 neutral present
   self.assertEqual(len(set(x['source_uid'] for x in got)),6)
   for r in manifest:
    self.assertEqual(sha(stable(r['messages'])),r['request_sha256'])
    if r['regime']!='present':self.assertFalse(any(m['content'].startswith('TRUSTED_EVIDENCE_RECORD:') for m in r['messages']))
 def test_feverous_evidence_resolves_without_label_leak(self):
  with tempfile.TemporaryDirectory() as td:
   td=pathlib.Path(td);claims=[];pages=[]
   for i,label in enumerate(['SUPPORTS','REFUTES','NOT ENOUGH INFO']*2):
    title=f'Fact {i}';eid=f'{title}_sentence_0';claims.append({'id':i,'claim':'Something to verify','label':label,
       'evidence':[{'content':[eid],'context':{eid:[f'{title}_title']}}]})
    pages.append({'title':title,'order':['sentence_0'],'sentence_0':'Evidence sentence '+str(i)})
   write_jsonl(td/'ann.jsonl',claims);write_jsonl(td/'wiki.jsonl',pages)
   cs,reject=feverous_candidates(td/'ann.jsonl',td/'wiki.jsonl',1000)
   self.assertEqual(len(select_balanced(cs,6,9)),6)
   self.assertIn('Evidence sentence 0',cs[0]['trusted'])
 def test_cell_lookup(self):
  page={'title':'Example','table_0':{'table':[[{'id':'header_cell_0_0_0','value':'Country'}],[{'id':'cell_0_1_0','value':'Germany'}]]}}
  self.assertEqual(page_element(page,'Example_cell_0_1_0'),'Germany')
 def test_decision_parser(self):
  self.assertEqual(parse_decision({'choices':[{'message':{'content':'{"verdict":"DEFER","rationale":"missing"}'}}]})['verdict'],'DEFER')
  self.assertIsNone(parse_decision({'choices':[{'message':{'content':'not json'}}]}))
 def test_ragtruth_split_and_freeze(self):
  with tempfile.TemporaryDirectory() as td:
   td=pathlib.Path(td); sources=[];resp=[]
   for i in range(12):
    sid=str(i);sources.append({'source_id':sid,'task_type':'QA','source_info':{'passages':'Trusted summary '+sid}})
    for j in range(2):
     resp.append({'id':sid+'-'+str(j),'source_id':sid,'response':'Claim x '+str(j),
                  'labels':[] if j else [{'text':'x','start':0,'end':1,'label_type':'Unsupported'}],
                  'split':'train' if i<6 else 'test','quality':'good'})
   write_jsonl(td/'resp.jsonl',resp);write_jsonl(td/'source.jsonl',sources)
   create(td/'resp.jsonl',td/'source.jsonl',td/'out',5,2,2,4,1000)
   from d1_local import verify_data
   rows=verify_data(td/'out')
   self.assertEqual(len(rows),10)
   self.assertEqual(len(set(x['source_uid'] for x in rows if x['split']=='test')),4)

if __name__=='__main__': unittest.main()
