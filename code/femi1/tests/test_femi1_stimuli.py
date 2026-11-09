import unittest
import femi1_stimuli as p

class ProtocolTests(unittest.TestCase):
    def setUp(self):
        self.x={
        'claim_id':'sample_fixture_not_an_experiment','family':'iris','seed':101,
        'selection_independent':False,'paired_rows':False,
        'selection_fault':True,'row_fault':True,'reference_verdict':'REJECT',
        'issuer':'coordinator_checked','schema_version':'femi1.1'}
    def test_false_overall_verdict_for_combined_fault(self):
        self.assertIn('APPROVE',p.message('T3','REJECT'))
        self.assertNotIn('REJECT',p.message('T3','REJECT'))
    def test_text_length_proxies(self):p.check_lengths()
    def test_full_record_stable(self):
        r1=p.treatment_request(self.x,'T1',0)
        r2=p.treatment_request(self.x,'T3',1)
        self.assertEqual(r1['trusted_sha256'],r2['trusted_sha256'])
        self.assertEqual(r1['request']['messages'][1],r2['request']['messages'][1])
        self.assertEqual(r1['request']['messages'][-1],r2['request']['messages'][-1])
    def test_false_verdict_rejected(self):
        bad=dict(self.x,reference_verdict='APPROVE')
        with self.assertRaises(AssertionError):p.validate(bad)
    def test_inventory_and_grouped_dependence(self):
        xs=[]
        for family in p.FAMILIES:
            for seed in p.SEEDS:
                for a,b in p.FAULTS:
                    x=dict(self.x,claim_id=f'{family}_{seed}_{a}{b}',family=family,seed=seed,
                      selection_fault=bool(a),row_fault=bool(b),selection_independent=not bool(a),paired_rows=not bool(b))
                    x['reference_verdict']=p.expected_verdict(x)
                    xs.append(x)
        trials=p.build_manifest(xs)
        self.assertEqual(len(trials),480)
        self.assertEqual(len({(z['family'],z['seed']) for z in trials}),8)
        self.assertEqual(len({(z['case_id'],z['treatment'],z['repeat']) for z in trials}),480)
        self.assertEqual([z['case_id'] for z in trials], [z['case_id'] for z in p.build_manifest(xs)])
    def test_separate_negative_control_inventory(self):
        trials=p.absent_evidence_controls()
        self.assertEqual(len(trials),8)
        self.assertTrue(all(t['expected_verdict']=='DEFER' for t in trials))
        self.assertTrue(all(len(t['request']['messages'])==3 for t in trials))
    def test_absence_control_has_no_note(self):
        r=p.treatment_request(self.x,'T0',0)
        self.assertEqual(len(r['request']['messages']),3)
        self.assertEqual(len(p.treatment_request(self.x,'T4',0)['request']['messages']),4)
if __name__=='__main__':unittest.main()
