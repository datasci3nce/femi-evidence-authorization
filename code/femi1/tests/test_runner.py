import json,sys,tempfile,unittest
from pathlib import Path
from unittest.mock import patch
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from femi1_stimuli import treatment_request
from femi1_live import execute,trial_id,read_done,checks_manifest,request_sha

class RunnerTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory()
        self.x={'claim_id':'fixture_only','family':'iris','seed':101,
                'selection_independent':True,'paired_rows':True,'reference_verdict':'APPROVE',
                'selection_fault':False,'row_fault':False,'issuer':'coordinator_checked','schema_version':'femi1.1'}
        self.requests=[treatment_request(self.x,t,0) for t in ('T1','T3')]
        self.out=Path(self.temp.name)/'out.jsonl'
        self.log=Path(self.temp.name)/'attempts.jsonl'
    def tearDown(self):self.temp.cleanup()

    @patch('femi1_live.send_request')
    def test_resume_does_not_recapture_or_modify_first_request(self,mock_send):
        mock_send.return_value=(200,{'choices':[{'message':{
            'content':json.dumps({'verdict':'APPROVE','rationale':'Fixture check','cited_checks':[]})}}]})
        self.assertEqual(execute(self.requests,self.out,self.log,'FAKE_NOT_REAL',limit=1,pace=0)[0],1)
        self.assertEqual(mock_send.call_count,1)
        self.assertEqual(execute(self.requests,self.out,self.log,'FAKE_NOT_REAL',pace=0)[0],1)
        self.assertEqual(mock_send.call_count,2)
        self.assertEqual(execute(self.requests,self.out,self.log,'FAKE_NOT_REAL',pace=0)[0],0)
        self.assertEqual(mock_send.call_count,2)
        _,seen=read_done(self.out)
        self.assertEqual(len(seen),2)
        for req in self.requests:
            self.assertEqual(seen[trial_id(req)]['request_sha256'],request_sha(req))

    @patch('femi1_live.send_request')
    def test_resume_refuses_modified_manifest(self,mock_send):
        mock_send.return_value=(200,{'choices':[{'message':{
            'content':json.dumps({'verdict':'DEFER','rationale':'fixture','cited_checks':[]})}}]})
        execute(self.requests,self.out,self.log,'FAKE_NOT_REAL',limit=1,pace=0)
        changed=[dict(z) for z in self.requests]
        changed[0]=dict(changed[0],request=dict(changed[0]['request']))
        changed[0]['request']['model']='WRONG_MODEL'
        with self.assertRaises(RuntimeError):execute(changed,self.out,self.log,'FAKE_NOT_REAL',pace=0)

    @patch('femi1_live.send_request')
    def test_transport_retries_preserve_exact_bytes(self,mock_send):
        mock_send.side_effect=[(429,{'error':'rate limited'}),(200,{'choices':[{'message':{
            'content':json.dumps({'verdict':'APPROVE','rationale':'fixture','cited_checks':[]})}}]})]
        with patch('femi1_live.time.sleep',return_value=None):
            execute(self.requests[:1],self.out,self.log,'FAKE_NOT_REAL',pace=0)
        self.assertEqual(mock_send.call_count,2)
        self.assertEqual(mock_send.call_args_list[0].args[0],mock_send.call_args_list[1].args[0])
        attempts=[json.loads(x) for x in self.log.read_text().splitlines()]
        self.assertEqual(len(attempts),2)
        self.assertEqual(attempts[0]['request_sha256'],attempts[1]['request_sha256'])

if __name__=='__main__':unittest.main()
