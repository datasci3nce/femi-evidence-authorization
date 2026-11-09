#!/usr/bin/env python3
"""Local d1-3B source-faithfulness benchmark (no paid API calls).

  probe  -> select and verify a compatible layer using TRAIN examples ONLY
  fit    -> fit activation direction on TRAIN, dose on DEV
  test   -> evaluate four arms ONCE on HELD-OUT TEST

Activation hooks target undoc'd model internals: fail closed on any mismatch.
"""
from __future__ import annotations
import argparse, collections, hashlib, json, math, os, pathlib, random, re, statistics, sys, time
from prepare import read_jsonl, file_sha

BASE_Q = 'Is the candidate response fully supported by the supplied trusted source material?'
INSTRUCTION_Q = ('Using only the TRUSTED SOURCE MATERIAL, assess the candidate response. '
    'Answer YES only if every factual claim in the candidate response is supported by that material; '
    'unsupported additions, contradictions, and outside knowledge do not count as support. '
    'Is the entire candidate response supported?')
ARMS=('unsteered','instruction_steered','activation_steered','random_sham')
DOSES=(0.25,0.5,1.0,2.0)

def read_data(d):
    d=pathlib.Path(d);fr=json.loads((d/'FREEZE.json').read_text())
    if file_sha(d/'d1_data_PRIVATE.jsonl')!=fr['data_sha256']:raise RuntimeError('Source data differs from freeze')
    rows=list(read_jsonl(d/'d1_data_PRIVATE.jsonl'))
    if len(rows)!=fr['n_train']+fr['n_dev']+fr['n_test']:raise RuntimeError('Frozen count mismatch')
    for p in ('train','dev','test'):
        if len([r for r in rows if r['partition']==p])!=fr['n_'+p]:raise RuntimeError('Partition count changed')
    bypart={p:set(r['source_id'] for r in rows if r['partition']==p) for p in ('train','dev','test')}
    for p,q in (('train','dev'),('train','test'),('dev','test')):
        if bypart[p]&bypart[q]:raise RuntimeError('SOURCE LEAK across '+p+'/'+q)
    if any(r['supported'] not in (0,1) for r in rows):raise RuntimeError('Invalid gold label')
    return fr,rows

def load_model():
    import torch
    from transformers import AutoModel
    if not torch.cuda.is_available():raise RuntimeError('GPU required for real model fit/test. Switch Colab Runtime > Change runtime type > GPU.')
    major=torch.cuda.get_device_capability(0)[0]
    dtype=torch.bfloat16 if major>=8 else torch.float16
    revision=os.getenv('D1_HF_REVISION','main')
    print('Loading LiquidAI/d1-3B',revision,'on',torch.cuda.get_device_name(),dtype,flush=True)
    model=AutoModel.from_pretrained('LiquidAI/d1-3B',revision=revision,trust_remote_code=True,dtype=dtype).to('cuda').eval()
    if not callable(getattr(model,'system_one',None)):
        raise RuntimeError('Loaded checkpoint does not expose system_one. Check Liquid model card and pinned code.')
    return torch,model

def model_revision(model):
    return {'requested_revision':os.getenv('D1_HF_REVISION','main'),
            'resolved_commit':getattr(getattr(model,'config',None),'_commit_hash',None),
            'class_name':type(model).__qualname__}

def parse_probability(r):
    try:p=float(r['answers']['supported']['noul'])
    except (ValueError,TypeError,KeyError,AttributeError) as e:raise RuntimeError(f'd1 system_one returned unexpected answer shape: {str(r)[:500]}') from e
    if not math.isfinite(p) or p<0 or p>1:raise RuntimeError(f'Invalid p_supported {p}')
    return p

def get_activation_tensor(out):
    # Pure tensor, or tuple whose first entry is a tensor. No opaque output rewriting.
    import torch
    if isinstance(out,torch.Tensor):return out,'tensor'
    if isinstance(out,tuple) and out and isinstance(out[0],torch.Tensor):return out[0],'tuple'
    return None,None

class ResidualHook:
    def __init__(self,model,path):
        mods=dict(model.named_modules())
        if path not in mods:raise RuntimeError('Unknown hook module: '+path)
        self.path=path;self.records=[];self.patches=0;self.vec=None;self.dose=0
        self.handle=mods[path].register_forward_hook(self._call)
    def _call(self,m,inputs,out):
        t,kind=get_activation_tensor(out)
        if t is None or t.ndim!=3 or not t.shape[1]:
            raise RuntimeError('Hook must return a single [batch,sequence,hidden] tensor. Cannot safely patch '+self.path)
        if t.shape[0]!=1:raise RuntimeError('Expected batch size 1 in selected hook')
        self.records.append(t[:, -1, :].detach().float().cpu().squeeze(0).clone())
        if self.vec is None or self.dose==0:return None
        if t.shape[-1]!=self.vec.numel():raise RuntimeError('Steering vector and module dimension mismatch')
        v=self.vec.to(device=t.device,dtype=t.dtype)*self.dose
        new=t.clone();new[:, -1, :]+=v;self.patches+=1
        return new if kind=='tensor' else (new,)+out[1:]
    def reset(self,vec=None,dose=0):self.records=[];self.patches=0;self.vec=vec;self.dose=dose
    def finish(self,expect_patch=False):
        if len(self.records)!=1:raise RuntimeError(f'Hook fired {len(self.records)} times, expected once. STOP.')
        if (self.patches==1)!=bool(expect_patch):raise RuntimeError('Steering did not patch exactly once. STOP.')
        return self.records[0]
    def close(self):self.handle.remove()

def query(model,state,question,hook,vec=None,dose=0):
    if hook:hook.reset(vec,dose)
    p=parse_probability(model.system_one(state,{'supported':{'type':'noul','instructions':question}}))
    h=hook.finish(expect_patch=(vec is not None and dose!=0)) if hook else None
    return p,h

def find_candidate_layers(model):
    # Only complete transformer-block module names, never arbitrary sublayers.
    pat=re.compile(r'^(.*?)(?:\.|^)(layers|blocks)\.(\d+)$')
    groups=collections.defaultdict(list)
    for name,_ in model.named_modules():
        m=pat.match(name)
        if m:groups[(m.group(1),m.group(2))].append((int(m.group(3)),name))
    # Largest block family, tie broken towards likely language model; model-dependent names are recorded.
    groups=[(k,sorted(v)) for k,v in groups.items() if len(v)>=8]
    if not groups:raise RuntimeError('No identifiable transformer-block family; use --hook-name to select a block after inspecting model.named_modules().')
    groups.sort(key=lambda kv:(len(kv[1]),'language' in kv[0][0],kv[0]),reverse=True)
    return groups

def probe(folder,hook_name=''):
    fr,rows=read_data(folder);train=[x for x in rows if x['partition']=='train']
    torch,model=load_model()
    if hook_name:
        candidates=[hook_name]
    else:
        groups=find_candidate_layers(model)
        family=groups[0][1]
        candidates=[name for _,name in family]
    counters=collections.defaultdict(list)
    handles=[]
    def callback(name):
        def fn(mod,ins,out):
            t,_=get_activation_tensor(out)
            counters[name].append(tuple(t.shape) if t is not None else None)
        return fn
    mods=dict(model.named_modules())
    for name in candidates:handles.append(mods[name].register_forward_hook(callback(name)))
    try:
        with torch.inference_mode():
            parse_probability(model.system_one(train[0]['state'],{'supported':{'type':'noul','instructions':BASE_Q}}))
    finally:
        for h in handles:h.remove()
    viable=[name for name in candidates if len(counters[name])==1 and counters[name][0] and len(counters[name][0])==3 and counters[name][0][0]==1 and counters[name][0][1]>=1]
    if not viable:raise RuntimeError('No compatible single-fire [batch,seq,hidden] transformer block; activation experiment is not valid on this build.')
    # Prespecified structural rule: nearest to ~75% of the depth, no performance or gold labels used.
    if hook_name:
        chosen=viable[0]
    else:
        index={name:i for i,name in enumerate(candidates)}
        target=0.75*(len(candidates)-1)
        chosen=min(viable,key=lambda name:(abs(index[name]-target),name))
    hk=ResidualHook(model,chosen)
    with torch.inference_mode():
        p,h=query(model,train[0]['state'],BASE_Q,hk)
    hk.close()
    item={'hook_name':chosen,'layer_probe_names':len(candidates),'compatible':len(viable),'shape':[1,1,int(h.numel())],
          'model':model_revision(model),'baseline_train_probability':p,'data_sha256':fr['data_sha256'],
          'selection_rule':'Nearest compatible transformer block to 75% of selected largest block family, using training stimulus; no outcome optimization.'}
    targetfile=pathlib.Path(folder)/'hook_probe.json'
    if targetfile.exists():
        previous=json.loads(targetfile.read_text())
        if previous!=item:raise RuntimeError('Existing hook probe differs. Do not silently replace.')
    else:targetfile.write_text(json.dumps(item,indent=2)+'\n')
    print(json.dumps(item,indent=2));return item

def score(records):
    if not records:raise RuntimeError('Empty predictions')
    neg=[r for r in records if r['y']==0];pos=[r for r in records if r['y']==1]
    if not neg or not pos:raise RuntimeError('Need both labels')
    n=len(records)
    ppos=sum(r['p']>=.5 for r in pos)/len(pos)
    negcorrect=sum(r['p']<.5 for r in neg)/len(neg)
    brier=sum((r['p']-r['y'])**2 for r in records)/n
    return {'n':n,'brier':brier,'balanced_accuracy':(ppos+negcorrect)/2,
            'false_accept_rate':1-negcorrect,'supported_accept_rate':ppos,
            'accuracy':sum(int(r['p']>=.5)==r['y'] for r in records)/n}

def fit(folder):
    folder=pathlib.Path(folder);fr,rows=read_data(folder)
    probe_file=folder/'hook_probe.json'
    if not probe_file.exists():raise RuntimeError('First run probe (training-only model hook test).')
    probeinfo=json.loads(probe_file.read_text())
    if probeinfo['data_sha256']!=fr['data_sha256']:raise RuntimeError('Hook probe came from different frozen corpus')
    if (folder/'d1_fitted.pt').exists():raise FileExistsError('Already fitted. Refusing to overwrite frozen direction.')
    torch,model=load_model()
    if model_revision(model)!=probeinfo['model']:raise RuntimeError('Model revision/config differs from hook probe')
    hook=ResidualHook(model,probeinfo['hook_name'])
    train=[r for r in rows if r['partition']=='train'];dev=[r for r in rows if r['partition']=='dev']
    features=collections.defaultdict(dict)
    with torch.inference_mode():
        for r in train:
            p,h=query(model,r['state'],BASE_Q,hook)
            features[r['source_id']][r['supported']]=h
    diffs=[]
    for sid,labels in features.items():
        if set(labels)!={0,1}:raise RuntimeError('TRAIN source not paired: '+sid)
        diffs.append(labels[1]-labels[0])
    d=torch.stack(diffs);avg=d.mean(0)
    mean_norm=float(torch.linalg.vector_norm(avg))
    if mean_norm<1e-9:raise RuntimeError('Zero learned contrast direction')
    magnitude=float(torch.median(torch.linalg.vector_norm(d,dim=1)))
    direction=(avg/mean_norm*magnitude).cpu()
    gen=torch.Generator(device='cpu').manual_seed(1947)
    randomvec=torch.randn(direction.shape,generator=gen)
    sham=(randomvec/randomvec.norm()*direction.norm()).cpu()
    coherence=mean_norm/float(torch.linalg.vector_norm(d,dim=1).mean())
    # Frozen dose search on DEV only; keep all arms and selected dose on test even when steering loses.
    dose_res=[]
    with torch.inference_mode():
        for dose in (0.0,)+DOSES:
            predictions=[]
            for r in dev:
                p,_=query(model,r['state'],BASE_Q,hook,direction,dose)
                predictions.append({'p':p,'y':r['supported']})
            dose_res.append({'dose':dose,**score(predictions)})
    base=dose_res[0]
    eligible=[q for q in dose_res[1:] if q['supported_accept_rate']>=base['supported_accept_rate']-0.1]
    if eligible:
        selected=max(eligible,key=lambda m:(m['balanced_accuracy'],-m['brier'],-m['dose']))
        selection='dev_balanced_accuracy_with_supported_acceptance_guardrail'
    else:
        selected=next(r for r in dose_res if r['dose']==.5)
        selection='fixed_default_0.5_due_to_failed_supported_acceptance_guardrail'
    # Intervention sensitivity check on up to six TRAIN cases, never a heldout sample.
    with torch.inference_mode():
        deltas=[]
        for r in train[:6]:
            unsteered,_=query(model,r['state'],BASE_Q,hook)
            steer,_=query(model,r['state'],BASE_Q,hook,direction,selected['dose'])
            deltas.append(abs(steer-unsteered))
    # Fail closed if patch fired but no observable probability perturbation on TRAIN.
    if max(deltas)<1e-7:
        raise RuntimeError('Steering hook fired, but intervention was output-inert on TRAIN. Cannot interpret steering effect; stop and inspect model internals.')
    payload={'direction':direction,'sham':sham,'selected_dose':float(selected['dose']),
             'model':model_revision(model),'hook_name':probeinfo['hook_name'],'data_sha256':fr['data_sha256'],
             'coherence':coherence,'n_train_pairs':len(features),'mean_diff_norm':mean_norm,'pair_median_norm':magnitude,
             'train_sensitivity_max_abs_delta':max(deltas),'selection_rule':selection,'dev_doses':dose_res,
             'protocol':'D1-SOURCE-FAITHFULNESS-v2; four heldout arms including random-sham'}
    torch.save(payload,folder/'d1_fitted.pt')
    hook.close()
    printable={k:v for k,v in payload.items() if k not in ('direction','sham')}
    print(json.dumps(printable,indent=2));
    if selected['balanced_accuracy']<=base['balanced_accuracy']:
        print('PRE-REGISTERED WARNING: No dev balanced-accuracy gain. Test still allowed as an informative negative result.')
    if coherence<.2:print('PRE-REGISTERED WARNING: low cross-pair direction coherence')

def pair_bootstrap(rows,arms=('activation_steered','random_sham','instruction_steered'),n_boot=3000,seed=1471):
    # Each test source appears once, hence source-level stratified bootstrap by TASK and GOLD.
    rng=random.Random(seed)
    groups=collections.defaultdict(list)
    for row in rows:
        if row['arm']=='unsteered':groups[(row['task'],row['gold_supported'])].append(row['response_id'])
    ids_by_group=list(groups.values())
    lookup={(r['response_id'],r['arm']):r for r in rows}
    def get_metrics(arm,selected):
        return score([{'p':lookup[(i,arm)]['prob_supported'],'y':lookup[(i,arm)]['gold_supported']} for i in selected])
    actual=[r['response_id'] for r in rows if r['arm']=='unsteered']
    base=get_metrics('unsteered',actual)
    report={}
    for arm in arms:
        treated=get_metrics(arm,actual)
        keys=('balanced_accuracy','false_accept_rate','supported_accept_rate','brier')
        obs={k:treated[k]-base[k] for k in keys}
        reps={k:[] for k in keys}
        for _ in range(n_boot):
            sampled=[rng.choice(group) for group in ids_by_group for j in range(len(group))]
            left=get_metrics('unsteered',sampled);right=get_metrics(arm,sampled)
            for k in keys:reps[k].append(right[k]-left[k])
        report[arm]={k:{'diff_vs_unsteered':obs[k], 'ci95':[sorted(reps[k])[int(.025*n_boot)],sorted(reps[k])[int(.975*n_boot)-1]]} for k in keys}
    return report

def heldout(folder):
    folder=pathlib.Path(folder);fr,rows=read_data(folder)
    outfile=folder/'d1_heldout_predictions.jsonl';partial=folder/'d1_heldout_PARTIAL.jsonl'
    if outfile.exists():raise FileExistsError('Heldout completed already. Run analyze; do not repeat.')
    fitfile=folder/'d1_fitted.pt'
    if not fitfile.exists():raise RuntimeError('Run fit first')
    import torch
    fititem=torch.load(fitfile,map_location='cpu',weights_only=True)
    if fititem['data_sha256']!=fr['data_sha256']:raise RuntimeError('Fit source changed')
    fit_hash=file_sha(fitfile)
    torch,model=load_model()
    if fititem['model']!=model_revision(model):raise RuntimeError('Fit/heldout checkpoint changed')
    hook=ResidualHook(model,fititem['hook_name'])
    test=[r for r in rows if r['partition']=='test']
    vectors={'unsteered':(BASE_Q,None,0.0),'instruction_steered':(INSTRUCTION_Q,None,0.0),
             'activation_steered':(BASE_Q,fititem['direction'],fititem['selected_dose']),
             'random_sham':(BASE_Q,fititem['sham'],fititem['selected_dose'])}
    expected={(r['id'],arm) for r in test for arm in ARMS}
    gold={r['id']:r for r in test}
    existing=list(read_jsonl(partial)) if partial.exists() else []
    completed=set()
    for p in existing:
        key=(p['response_id'],p['arm'])
        if key not in expected or key in completed:raise RuntimeError('Duplicate or foreign partial record. STOP.')
        r=gold[p['response_id']]
        if (p['source_id']!=r['source_id'] or p['task']!=r['task'] or p['gold_supported']!=r['supported'] or
            p['fit_sha256']!=fit_hash or p['data_sha256']!=fr['data_sha256']):raise RuntimeError('Partial checkpoint mismatch. STOP.')
        completed.add(key)
    print('Heldout resume:',len(completed),'/',len(expected),'existing records')
    with torch.inference_mode():
        with partial.open('a',encoding='utf8') as f:
            for r in test:
                perm=list(ARMS);random.Random(9000+int(hashlib.sha256(r['id'].encode()).hexdigest()[:8],16)).shuffle(perm)
                for arm in perm:
                    if (r['id'],arm) in completed:continue
                    q,vec,dose=vectors[arm]
                    torch.cuda.synchronize();t0=time.perf_counter()
                    p,_=query(model,r['state'],q,hook,vec,dose)
                    torch.cuda.synchronize()
                    rec={'response_id':r['id'],'source_id':r['source_id'],'task':r['task'],
                        'gold_supported':r['supported'],'arm':arm,'prob_supported':p,'dose':dose,
                        'elapsed_seconds':time.perf_counter()-t0,'fit_sha256':fit_hash,'data_sha256':fr['data_sha256']}
                    f.write(json.dumps(rec,sort_keys=True)+'\n');f.flush()
                    completed.add((r['id'],arm))
                if len(completed)%40==0:print('Completed',len(completed),'/',len(expected),flush=True)
    hook.close()
    if completed!=expected:raise RuntimeError('Heldout inventory incomplete. Partial file retained; no analysis.')
    os.replace(partial,outfile)
    print('Saved complete',outfile,'with',len(completed),'predictions')
    analyze(folder)

def analyze(folder):
    folder=pathlib.Path(folder);fr,rows=read_data(folder);path=folder/'d1_heldout_predictions.jsonl'
    preds=list(read_jsonl(path));test=[r for r in rows if r['partition']=='test']
    expected={(r['id'],arm) for r in test for arm in ARMS}
    if len(preds)!=len(expected) or {(p['response_id'],p['arm']) for p in preds}!=expected:
        raise RuntimeError('Expected every test response × every arm exactly once')
    gold={r['id']:r for r in test}
    for p in preds:
        r=gold[p['response_id']]
        if p['gold_supported']!=r['supported'] or p['source_id']!=r['source_id'] or p['task']!=r['task']:
            raise RuntimeError('Prediction metadata differs from frozen ground truth')
        if not 0<=p['prob_supported']<=1:raise RuntimeError('Invalid probability')
    metrics={}
    for arm in ARMS:
        subset=[r for r in preds if r['arm']==arm]
        metrics[arm]={**score([{'p':r['prob_supported'],'y':r['gold_supported']} for r in subset]),
                     'per_task':{task:score([{'p':r['prob_supported'],'y':r['gold_supported']} for r in subset if r['task']==task]) for task in ('QA','Summary','Data2txt')},
                     'median_seconds':statistics.median(r['elapsed_seconds'] for r in subset)}
    boot=pair_bootstrap(preds)
    a,b,s=metrics['activation_steered'],metrics['unsteered'],metrics['random_sham']
    assessment={'balanced_accuracy_gain_vs_unsteered':a['balanced_accuracy']-b['balanced_accuracy'],
      'supported_acceptance_drop':b['supported_accept_rate']-a['supported_accept_rate'],
      'balanced_accuracy_gain_vs_sham':a['balanced_accuracy']-s['balanced_accuracy'],
      'passes_exploratory_success_gate':(a['balanced_accuracy']>b['balanced_accuracy'] and a['balanced_accuracy']>s['balanced_accuracy'] and a['supported_accept_rate']>=b['supported_accept_rate']-.05),
      'interpretation':'Exploratory gate only; positive outcome requires uncertainty intervals and negative controls. No real-world authorization capability is demonstrated.'}
    report={'n_test':len(test),'n_decisions':len(preds),'frozen_data_sha256':fr['data_sha256'],
       'metrics':metrics,'stratified_paired_bootstrap_differences':boot,'assessment':assessment,
       'note':'Annotations are observed unsupported spans; this is response-level source-faithfulness, not FEMI authorization verification.'}
    (folder/'d1_heldout_metrics.json').write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps(report,indent=2))

def source_withholding(folder):
    """Secondary sensitivity check: same candidate response, trusted source removed.

    No gold correctness claim is assigned to the modified items; this measures
    whether a model is sensitive to removing source content, not hallucination F1.
    """
    folder=pathlib.Path(folder);fr,rows=read_data(folder)
    pred_file=folder/'d1_heldout_predictions.jsonl'
    if not pred_file.exists():raise RuntimeError('Complete heldout test before source-removal diagnostic')
    outfile=folder/'d1_source_withheld.jsonl'
    if outfile.exists():raise FileExistsError('Source-removal result exists; do not repeat.')
    preds=list(read_jsonl(pred_file))
    lookup={(p['response_id'],p['arm']):p for p in preds}
    torch,model=load_model()
    fit=torch.load(folder/'d1_fitted.pt',map_location='cpu',weights_only=True)
    if fit['data_sha256']!=fr['data_sha256'] or fit['model']!=model_revision(model):raise RuntimeError('Frozen fit/model mismatch')
    hook=ResidualHook(model,fit['hook_name'])
    selected=[r for r in rows if r['partition']=='test' and r['supported']==1]
    result=[]
    sep='\n\nCANDIDATE RESPONSE TO AUDIT:\n'
    with torch.inference_mode():
        for r in selected:
            if sep not in r['state']:raise RuntimeError('Bad source-state delimiter')
            candidate=r['state'].split(sep,1)[1]
            state='TRUSTED SOURCE MATERIAL:\n[NO TRUSTED SOURCE PROVIDED]'+sep+candidate
            for arm,vec in (('unsteered',None),('activation_steered',fit['direction'])):
                dose=fit['selected_dose'] if vec is not None else 0
                p,_=query(model,state,BASE_Q,hook,vec,dose)
                ref=lookup[(r['id'],arm)]['prob_supported']
                result.append({'response_id':r['id'],'source_id':r['source_id'],'task':r['task'],
                    'arm':arm,'prob_with_source':ref,'prob_without_source':p,
                    'drop_on_withholding':ref-p})
    hook.close()
    if len(result)!=len(selected)*2:raise RuntimeError('Source ablation inventory incomplete')
    outfile.write_text(''.join(json.dumps(r,sort_keys=True)+'\n' for r in result))
    summary={arm:{'n':len([r for r in result if r['arm']==arm]),
                 'mean_probability_drop':statistics.mean(r['drop_on_withholding'] for r in result if r['arm']==arm),
                 'median_probability_drop':statistics.median(r['drop_on_withholding'] for r in result if r['arm']==arm),
                 'fraction_probability_decreases':statistics.mean(r['drop_on_withholding']>0 for r in result if r['arm']==arm)}
             for arm in ('unsteered','activation_steered')}
    (folder/'d1_source_withheld_summary.json').write_text(json.dumps(summary,indent=2)+'\n')
    print(json.dumps(summary,indent=2))
    print('NOTE: this is an unlabeled source-removal sensitivity test, not a gold-standard attribution test.')

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument('action',choices=['preflight','probe','fit','test','analyze','ablate'])
    ap.add_argument('--dir',required=True);ap.add_argument('--hook-name',default='')
    a=ap.parse_args()
    if a.action=='preflight':
        fr,rows=read_data(a.dir)
        print('Frozen dataset verified:',fr['n_train'],fr['n_dev'],fr['n_test'])
        print(fr['per_partition_task_label'])
    elif a.action=='probe':probe(a.dir,a.hook_name)
    elif a.action=='fit':fit(a.dir)
    elif a.action=='test':heldout(a.dir)
    elif a.action=='ablate':source_withholding(a.dir)
    else:analyze(a.dir)
if __name__=='__main__':main()
