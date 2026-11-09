import json, pathlib, sys, tempfile, unittest
ROOT=pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'src'))
from build_transfer import read_jsonl,stable,sha
from run_and_score import verify_manifest,expand,model_config,analyze
from cross_analysis import analyze as cross_analyze

class OfflineScoringTests(unittest.TestCase):
    def test_synthetic_full_scoring(self):
        # These are generated test fixtures, NOT research model results.
        with tempfile.TemporaryDirectory() as td:
            folder=pathlib.Path(td)/'cross';folder.mkdir()
            for f in ['manifest.jsonl','FREEZE.json','cases_PRIVATE.jsonl']:
                (folder/f).write_bytes((ROOT/'runs/cross_model'/f).read_bytes())
            rs=folder/'results';rs.mkdir()
            rows=verify_manifest(folder)
            models=model_config(ROOT/'models.cross.v2.json')['models']
            expanded=expand(rows,models)
            with (rs/'responses.jsonl').open('w') as out:
                for t in expanded:
                    payload={'model':t['model_id'],'messages':t['messages'],'temperature':0.2,'max_tokens':1600}
                    if t.get('provider_constraint'):payload['provider']=t['provider_constraint']
                    verdict=t['expected_verdict']
                    parsed={'verdict':verdict,'rationale':'synthetic fixture','cited_evidence':[]}
                    raw={'choices':[{'message':{'content':json.dumps(parsed)}}], 'provider':t['provider_constraint']['order'][0],'usage':{'cost':0.0}}
                    out.write(stable({'trial_id':t['trial_id'],'request_sha256':sha(stable(payload)),
                        'model_name':t['model_name'],'model_id':t['model_id'], 'result':raw,'parsed':parsed})+'\n')
            class A:pass
            a=A();a.dir=str(folder);a.models=str(ROOT/'models.cross.v2.json');a.domain=None
            analyze(a)
            self.assertEqual(len(list(read_jsonl(rs/'responses.jsonl'))),864)
            r=cross_analyze(folder,ROOT/'models.cross.v2.json')
            self.assertEqual(r['n_responses'],864)
            self.assertEqual(sum(x['unauthorized'] for x in r['summary'].values()),0)
            self.assertEqual(len(r['difference_in_differences']),4)

if __name__=='__main__':unittest.main()
