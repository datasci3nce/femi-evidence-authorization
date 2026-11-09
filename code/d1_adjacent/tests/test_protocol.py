import unittest, tempfile, pathlib, json, sys, collections
from unittest.mock import patch
sys.path.insert(0,str(pathlib.Path(__file__).resolve().parents[1]/'src'))
import prepare, d1_experiment as d1

TASKS=prepare.TASKS

def fixture(folder):
    folder=pathlib.Path(folder);sfile=folder/'source_info.jsonl';rfile=folder/'response.jsonl'
    sources=[];responses=[];idx=0
    for task in TASKS:
        # train: 8 paired sources + 20 extra sources for balanced dev
        for ix in range(28):
            sid=f'{task}-train-{ix}';sources.append({'source_id':sid,'task_type':task,'source_info':{'passages':'Example fact A and fact B','question':'Example?'},'source':'demo'})
            labels=(0,1) if ix<8 else ((ix%2),)
            for y in labels:
                idx+=1;responses.append({'id':str(idx),'source_id':sid,'split':'train','quality':'good','response':'Example fact A' if y==1 else 'Example fact C', 'labels':[] if y else [{'text':'Example fact C','label_type':'Evident Baseless Info'}]})
        # original test: 40 distinct sources per task, 20 each label
        for ix in range(40):
            sid=f'{task}-test-{ix}';sources.append({'source_id':sid,'task_type':task,'source_info':'Example fact A','source':'demo'})
            y=ix%2;idx+=1
            responses.append({'id':str(idx),'source_id':sid,'split':'test','quality':'good','response':'Example fact A' if y else 'Example fact C','labels':[] if y else [{'text':'Example fact C','label_type':'Evident Baseless Info','implicit_true':False}]})
    sfile.write_bytes(prepare.jsonl_bytes(sources));rfile.write_bytes(prepare.jsonl_bytes(responses))
    return sfile,rfile

class TestFrozenCorpus(unittest.TestCase):
    def test_balance_and_source_separation(self):
        with tempfile.TemporaryDirectory() as td:
            s,r=fixture(td)
            info=prepare.build(r,s,pathlib.Path(td)/'run')
            self.assertEqual((info['n_train'],info['n_dev'],info['n_test']),(48,60,120))
            fr,rows=d1.read_data(pathlib.Path(td)/'run')
            self.assertEqual(fr['data_sha256'],prepare.file_sha(pathlib.Path(td)/'run'/'d1_data_PRIVATE.jsonl'))
            self.assertEqual(set(fr['per_partition_task_label']['test'].values()),{20})
            self.assertEqual(set(fr['per_partition_task_label']['dev'].values()),{10})
            with self.assertRaises(FileExistsError):prepare.build(r,s,pathlib.Path(td)/'run')
            self.assertNotIn('labels',rows[0]['state'])
    def test_mutation_fails_closed(self):
        with tempfile.TemporaryDirectory() as td:
            s,r=fixture(td);run=pathlib.Path(td)/'run'
            prepare.build(r,s,run)
            with (run/'d1_data_PRIVATE.jsonl').open('a') as f:f.write('{}\n')
            with self.assertRaises(RuntimeError):d1.read_data(run)
    def test_classification_metrics_penalize_always_negative(self):
        records=[{'y':0,'p':.01} for _ in range(10)]+[{'y':1,'p':.01} for _ in range(10)]
        m=d1.score(records)
        self.assertEqual(m['false_accept_rate'],0)
        self.assertEqual(m['supported_accept_rate'],0)
        self.assertEqual(m['balanced_accuracy'],.5)

class TestHook(unittest.TestCase):
    def test_forward_hook_modifies_hidden_state(self):
        import torch
        class Model(torch.nn.Module):
            def __init__(self):
                super().__init__();self.layer=torch.nn.Identity()
            def system_one(self,state,questions):
                x=torch.tensor([[[1.,2.,3.]]]);y=self.layer(x)
                return {'answers':{'supported':{'noul':float(torch.sigmoid(y[0,-1,0]).item())}}}
        model=Model();hook=d1.ResidualHook(model,'layer')
        try:
            a,_=d1.query(model,'s','?',hook)
            b,_=d1.query(model,'s','?',hook,torch.tensor([2.,0.,0.]),1)
            self.assertGreater(b,a)
            self.assertEqual(len(hook.records),1)
        finally:hook.close()
    def test_incompatible_hook_fails_closed(self):
        import torch
        class Model(torch.nn.Module):
            def __init__(self):super().__init__();self.layer=torch.nn.Identity()
            def system_one(self,s,q):
                self.layer(torch.ones(2,3));return {'answers':{'supported':{'noul':.5}}}
        model=Model();hook=d1.ResidualHook(model,'layer')
        try:
            with self.assertRaises(RuntimeError):d1.query(model,'s','?',hook)
        finally:hook.close()

class TestScoring(unittest.TestCase):
    def test_synthetic_prediction_inventory(self):
        with tempfile.TemporaryDirectory() as td:
            s,r=fixture(td);run=pathlib.Path(td)/'run'
            prepare.build(r,s,run);fr,rows=d1.read_data(run)
            preds=[]
            for r in rows:
                if r['partition']!='test':continue
                for arm in d1.ARMS:
                    p=.8 if r['supported'] else .2
                    if arm=='random_sham':p=.7 if r['supported'] else .3
                    preds.append({'response_id':r['id'],'source_id':r['source_id'],'task':r['task'],
                        'gold_supported':r['supported'],'arm':arm,'prob_supported':p,
                        'elapsed_seconds':.01})
            (run/'d1_heldout_predictions.jsonl').write_bytes(prepare.jsonl_bytes(preds))
            d1.analyze(run)
            summary=json.loads((run/'d1_heldout_metrics.json').read_text())
            self.assertEqual(summary['n_decisions'],480)
            self.assertEqual(summary['metrics']['unsteered']['balanced_accuracy'],1.0)
            self.assertFalse(summary['assessment']['passes_exploratory_success_gate'])
            preds.pop();(run/'d1_heldout_predictions.jsonl').write_bytes(prepare.jsonl_bytes(preds))
            with self.assertRaises(RuntimeError):d1.analyze(run)

if __name__=='__main__':unittest.main()
