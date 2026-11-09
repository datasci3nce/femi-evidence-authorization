import copy,io,json,sys,tempfile,unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from femi1_cases import generate,independent_verify_execution
from femi1_stimuli import load_jsonl,build_manifest,absent_evidence_controls
from femi1_live import checks_manifest,trial_id,request_sha,json_verdict
from femi1_analysis import summary

class OfflineExecutionTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temp=tempfile.TemporaryDirectory()
        cls.root=Path(cls.temp.name)
        cls.verification=generate(cls.root)
        cls.cases=load_jsonl(cls.root/'cases.jsonl')
        cls.manifest=build_manifest(cls.cases)
        cls.controls=absent_evidence_controls()
    @classmethod
    def tearDownClass(cls):cls.temp.cleanup()

    def test_all_32_cases_and_truth_from_independent_verifier(self):
        self.assertEqual(len(self.cases),32)
        self.assertEqual(self.verification['counts_by_reference_verdict'],{'APPROVE':8,'REJECT':24})
        for case in self.cases:
            record=json.loads((self.root/'coordinator_ledgers'/f'{case["claim_id"]}.json').read_text())
            independent=independent_verify_execution(record)
            self.assertEqual(independent['reference_verdict'],case['reference_verdict'])
            self.assertEqual(independent['selection_independent'],case['selection_independent'])
            self.assertEqual(independent['paired_rows'],case['paired_rows'])

    def test_corruption_detected(self):
        c=self.cases[0]
        raw=json.loads((self.root/'coordinator_ledgers'/f'{c["claim_id"]}.json').read_text())
        broken=copy.deepcopy(raw)
        next(x for x in broken['ledger'] if x['kind']=='metric')['accuracy']=0.1234
        with self.assertRaises(AssertionError):independent_verify_execution(broken)

    def test_manifest_inventory_and_paired_evidence_hashes(self):
        checks_manifest(self.manifest,480)
        checks_manifest(self.controls,8,controls=True)
        same=[z for z in self.manifest if z['case_id']==self.cases[0]['claim_id']]
        self.assertEqual(len(same),15)
        self.assertEqual(len(set(z['trusted_sha256'] for z in same)),1)
        self.assertEqual(len(set(z['request']['messages'][1]['content'] for z in same)),1)
        self.assertEqual(len(set(z['request_sha256'] for z in same if 'request_sha256' in z)),0)

    def test_T3_has_wrong_overall_verdict_both_valid_and_invalid(self):
        for case in self.cases:
            trial=next(z for z in self.manifest if z['case_id']==case['claim_id'] and z['treatment']=='T3')
            note=trial['request']['messages'][2]['content']
            if case['reference_verdict']=='APPROVE':
                self.assertIn('supports REJECT',note)
            else:
                self.assertIn('supports APPROVE',note)

    def test_no_treatment_labels_leak_in_model_messages(self):
        for z in self.manifest:
            blob=json.dumps(z['request']['messages'])
            self.assertNotIn('"treatment"',blob)
            self.assertNotIn('FEMI-1',blob)
            self.assertNotIn('selection_fault',blob)
            self.assertNotIn('row_fault',blob)
            self.assertNotIn('sel0',blob)
            self.assertNotIn('sel1',blob)
            self.assertNotIn('row0',blob)
            self.assertNotIn('row1',blob)
            self.assertTrue(z['case_id'].startswith('case_'))

    def test_json_parser_never_maps_bad_output_to_defer(self):
        for content in ('not json','{"verdict":"WAIT","rationale":"x","cited_checks":[]}',
                        '{"verdict":"DEFER","rationale":"x"}'):
            payload={'choices':[{'message':{'content':content}}]}
            v,c,e=json_verdict(payload)
            self.assertIsNone(v)
            self.assertIsNotNone(e)

    def test_cluster_scoring_fixtures_not_model_results(self):
        def fake_response(z,verdict):
            return {'trial_id':trial_id(z),'request_sha256':request_sha(z),
                    'http_status':200,'response':{'choices':[{'message':{
                    'content':json.dumps({'verdict':verdict,'rationale':'FIXTURE unit test only',
                                         'cited_checks':['selection_independent','paired_rows']})}}]}}
        rows=[]
        for z in self.manifest:
            verdict='DEFER' if z['treatment']=='T3' else z['reference_verdict']
            rows.append(fake_response(z,verdict))
        ctrls=[fake_response(z,'DEFER') for z in self.controls]
        result,_=summary(self.manifest,rows,self.controls,ctrls)
        self.assertEqual(result['primary_clustered_effects']['T2_minus_T4']['point_estimate'],0)
        self.assertEqual(result['primary_clustered_effects']['T3_minus_T4']['point_estimate'],-1)
        self.assertEqual(result['absent_evidence_controls']['deferred'],8)
        self.assertEqual(len(result['cluster_balance_rows']),8)
        self.assertEqual(sum(r['correct_decisive'] for r in result['by_treatment_and_fault'] if r['treatment']=='T3'),0)

if __name__=='__main__':unittest.main()
