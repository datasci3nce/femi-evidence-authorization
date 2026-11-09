#!/usr/bin/env python3
"""Local d1-3B study. Requires GPU, transformers>=5.14, torch. No API calls.

Important: activation steering is OPTIONAL and experimental. Fail closed on hook/mode mismatch.
Model forward hook internals are NOT guaranteed by Liquid AI's documented system_one API.
"""
import argparse, collections, hashlib, json, math, pathlib, random, statistics, sys, os, time
from build_transfer import read_jsonl,sha
BASE_QUESTION='Is every factual assertion in the candidate response fully supported by the supplied source document?'
STEERED_QUESTION=('Answer YES only if each factual assertion is explicitly supported by the supplied SOURCE_DOCUMENT. '
                  'Treat outside knowledge, plausible guesses, and assertions in the CANDIDATE_RESPONSE as insufficient evidence. '
                  'Is the entire candidate response supported?')

def load_torch_model():
    try:
        import torch
        from transformers import AutoModel
    except ImportError as e: raise RuntimeError('Install torch and transformers>=5.14 first') from e
    if not torch.cuda.is_available(): raise RuntimeError('GPU required for activation-steering protocol')
    cc_major=torch.cuda.get_device_capability(0)[0]
    dtype=torch.bfloat16 if cc_major>=8 else torch.float16  # T4 (SM 7.5) needs fp16
    print('Loading d1 on GPU with',dtype,'requested revision:',os.getenv('D1_HF_REVISION','main'))
    model=AutoModel.from_pretrained('LiquidAI/d1-3B',revision=os.getenv('D1_HF_REVISION','main'),trust_remote_code=True,dtype=dtype).to('cuda')
    model.eval(); return torch,model

def extract_tensor(obj):
    try:
        import torch
    except ImportError:return None,None
    if isinstance(obj,torch.Tensor):return obj,None
    if isinstance(obj,tuple) and obj and isinstance(obj[0],torch.Tensor):return obj[0],tuple
    return None,None

class Hook:
    def __init__(self,model,name,torch):
        mods=dict(model.named_modules())
        if name not in mods:raise ValueError('Unknown module '+name+'; use --list-hooks to inspect valid names')
        self.vec=None;self.dose=0;self.torch=torch;self.captured=[];self.patched=0
        self.handle=mods[name].register_forward_hook(self.fn)
    def fn(self,module,inputs,out):
        t,wr=extract_tensor(out)
        if t is None or t.ndim!=3:raise RuntimeError('Hook output incompatible; expected [batch, sequence, hidden]')
        x=t[:, -1, :].detach().float().cpu();self.captured.append(x.squeeze(0).clone())
        if self.vec is None or self.dose==0:return None
        if t.shape[-1]!=self.vec.numel(): raise RuntimeError('Steering dimension mismatch')
        v=self.vec.to(t.device,dtype=t.dtype)*self.dose
        y=t.clone();y[:,-1,:]+=v;self.patched+=1
        if wr is tuple:return (y,)+out[1:]
        return y
    def start(self,vec=None,dose=0):self.captured=[];self.patched=0;self.vec=vec;self.dose=dose
    def stop(self,expected_patched=False):
        if len(self.captured)!=1:raise RuntimeError(f'Expected exactly 1 activation observation; captured {len(self.captured)}. Wrong hook or multi-forward model; STOP.')
        if expected_patched and self.patched!=1:raise RuntimeError('Steering did not patch exactly once; STOP')
        return self.captured[0]
    def close(self):self.handle.remove()

def prob(model,state,question,hook=None,vec=None,dose=0):
    if hook:hook.start(vec,dose)
    result=model.system_one(state,{'grounded':{'type':'noul','instructions':question}})
    a=result.get('answers',{}).get('grounded',{})
    p=float(a['noul'])
    if not 0<=p<=1:raise RuntimeError('Bad probability '+str(p))
    h=hook.stop(expected_patched=vec is not None and dose!=0) if hook else None
    return p,h

def brier(rows):return sum((p-y)**2 for p,y in rows)/len(rows)
def metrics(pred):
    n=len(pred);tp=sum(p>=0.5 and y==1 for p,y in pred);fp=sum(p>=0.5 and y==0 for p,y in pred)
    neg=sum(y==0 for _,y in pred);pos=n-neg
    return {'n':n,'brier':brier(pred),'accuracy':sum((p>=.5)==bool(y) for p,y in pred)/n,
       'false_accept_rate':fp/neg if neg else None,'supported_accept_rate':tp/pos if pos else None}

def verify_data(folder):
    p=pathlib.Path(folder);d=json.loads((p/'FREEZE.json').read_text())
    digest=hashlib.sha256((p/'d1_data_PRIVATE.jsonl').read_bytes()).hexdigest()
    if digest!=d['data_sha256']:raise RuntimeError('d1 freeze changed')
    rows=list(read_jsonl(p/'d1_data_PRIVATE.jsonl'))
    src_by_split=collections.defaultdict(set)
    for r in rows:src_by_split[r['split']].add(r['source_uid'])
    for a,b in [('train','dev'),('train','test'),('dev','test')]:
        assert not src_by_split[a]&src_by_split[b], 'SOURCE LEAK: '+a+'/'+b
    return rows

def save_records(path,records):
    path.write_text('\n'.join(json.dumps(x,sort_keys=True) for x in records)+'\n')

def fit(folder,hook_name,seed):
    import torch
    rows=verify_data(folder);train=[x for x in rows if x['split']=='train'];dev=[x for x in rows if x['split']=='dev']
    torch,model=load_torch_model();hook=Hook(model,hook_name,torch)
    features=collections.defaultdict(dict)
    print('Collecting paired training features, no dev/test used for fit')
    with torch.inference_mode():
        for x in train:
            _,activation=prob(model,x['state'],BASE_QUESTION,hook)
            features[x['source_uid']][x['supported']]=activation
    diffs=[]
    for sid,refs in features.items():
        if set(refs)!={0,1}:raise RuntimeError('Missing one label in paired source: '+sid)
        diffs.append(refs[1]-refs[0])
    import torch as tt
    d=tt.stack(diffs);avg=d.mean(0);mean_norm=float(tt.linalg.vector_norm(avg));median_pair_norm=float(tt.median(tt.linalg.vector_norm(d,dim=1)))
    if not mean_norm:raise RuntimeError('Zero steering direction')
    coherence=mean_norm / float(tt.linalg.vector_norm(d,dim=1).mean())
    # feature scale in native hidden units, not arbitrary unit vector.
    direction=avg/mean_norm*median_pair_norm
    rng=tt.Generator().manual_seed(seed+99);sham=tt.randn(direction.shape,generator=rng);sham=sham/sham.norm()*direction.norm()
    doses=[0.0,0.25,0.5,1.0]
    results=[]
    with tt.inference_mode():
        for dose in doses:
            obs=[]
            for x in dev:
                p,_=prob(model,x['state'],BASE_QUESTION,hook,direction,dose)
                obs.append((p,x['supported']))
            results.append({'dose':dose,**metrics(obs)})
    # Always evaluate a real nonzero intervention on holdout; development picks among nonzero doses.
    # Report its comparison with zero; never silently rename dose zero as a steered arm.
    best=min((x for x in results if x['dose']>0),key=lambda x:(x['brier'],x['dose']))
    content={'checkpoint':'LiquidAI/d1-3B','hf_revision_requested':os.getenv('D1_HF_REVISION','main'),
        'model_config_commit':getattr(model.config,'_commit_hash',None),'hook_name':hook_name,'direction':direction.cpu(),
        'sham':sham.cpu(),'selected_dose':best['dose'],'fit_train_sources':len(features),
        'coherence':coherence,'mean_norm':mean_norm,'median_pair_norm':median_pair_norm,
        'development_results':results,'seed':seed,
        'data_sha256':json.loads((pathlib.Path(folder)/'FREEZE.json').read_text())['data_sha256']}
    tt.save(content,pathlib.Path(folder)/'d1_fitted.pt')
    hook.close();print(json.dumps({k:v for k,v in content.items() if k not in ('direction','sham')},indent=2))
    baseline=next(x for x in results if x['dose']==0)
    if best['brier']>=baseline['brier']:print('WARNING: Dev found NO improvement at any tested nonzero steering dose; still run the prespecified heldout comparison and report the failure.')
    if coherence<0.2:print('WARNING: very low feature coherence; do not claim a stable steering direction.')

def evaluate(folder,hook_name):
    import torch
    rows=verify_data(folder);test=[x for x in rows if x['split']=='test']
    fit_path=pathlib.Path(folder)/'d1_fitted.pt'
    if not fit_path.exists():raise RuntimeError('Run --fit on TRAIN/DEV before testing')
    item=torch.load(fit_path,map_location='cpu',weights_only=True)
    frozen=json.loads((pathlib.Path(folder)/'FREEZE.json').read_text())
    if item['data_sha256']!=frozen['data_sha256'] or item['hook_name']!=hook_name:raise RuntimeError('Fitted file mismatch')
    torch,model=load_torch_model();hook=Hook(model,hook_name,torch)
    if item.get('hf_revision_requested')!=os.getenv('D1_HF_REVISION','main'):
        raise RuntimeError('d1 model revision selection changed between fit and heldout')
    if item.get('model_config_commit') and getattr(model.config,'_commit_hash',None) and item['model_config_commit']!=getattr(model.config,'_commit_hash',None):
        raise RuntimeError('d1 actual model commit changed between fit and heldout')
    arms={'unsteered':(BASE_QUESTION,None,0),
          'instruction_steered':(STEERED_QUESTION,None,0),
          'activation_steered':(BASE_QUESTION,item['direction'],item['selected_dose']),
          'random_sham':(BASE_QUESTION,item['sham'],item['selected_dose'])}
    records=[]
    with torch.inference_mode():
        for x in test:
            for arm,(question,vec,dose) in arms.items():
                torch.cuda.synchronize()
                tick=time.perf_counter();p,_=prob(model,x['state'],question,hook,vec,dose)
                torch.cuda.synchronize();elapsed_s=time.perf_counter()-tick
                records.append({'response_id':x['response_id'],'source_uid':x['source_uid'],
                                'task_type':x['task_type'],'gold_supported':x['supported'],
                                'arm':arm,'prob_supported':p,'dose':dose,'elapsed_s':elapsed_s})
    hook.close();outfile=pathlib.Path(folder)/'d1_heldout_predictions.jsonl';save_records(outfile,records)
    report={arm:metrics([(x['prob_supported'],x['gold_supported']) for x in records if x['arm']==arm]) for arm in arms}
    report['selected_dose']=item['selected_dose']; report['coherence']=item['coherence']
    report['requested_hf_revision']=item['hf_revision_requested'];report['actual_model_commit']=item['model_config_commit']
    for arm in arms:report[arm]['median_elapsed_s']=statistics.median(x['elapsed_s'] for x in records if x['arm']==arm)
    (pathlib.Path(folder)/'d1_heldout_metrics.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report,indent=2))

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('action',choices=['list-hooks','fit','test']);p.add_argument('--dir',required=True)
    p.add_argument('--hook-name',default='');p.add_argument('--seed',type=int,default=125)
    a=p.parse_args()
    if a.action=='list-hooks':
        t,model=load_torch_model()
        names=[name for name,_ in model.named_modules() if name and ('layers' in name or 'blocks' in name)]
        print('\n'.join(names[-150:]));print('Choose a full 3D-residual module path. This list is not proof a hook is compatible.');sys.exit()
    if not a.hook_name:raise SystemExit('--hook-name required for fit/test; first run list-hooks')
    if a.action=='fit':fit(a.dir,a.hook_name,a.seed)
    else:evaluate(a.dir,a.hook_name)
