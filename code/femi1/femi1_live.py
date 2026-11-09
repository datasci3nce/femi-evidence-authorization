"""OpenRouter runner for the frozen FEMI-1 JSONL manifest.

Never invents inference outputs. Safe resume appends one terminal row per planned
trial. Exact serialized request bytes are archived via manifest + SHA256; each
transport attempt is logged. Uses env OPENROUTER_API_KEY or HANDOFF_API_KEY.
"""
from __future__ import annotations
import argparse
import re
from datetime import datetime, timezone
import hashlib, json, os, random, time
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen
from femi1_stimuli import canonical, load_jsonl

API_URL='https://openrouter.ai/api/v1/chat/completions'
TRANSPORT_MAX_RETRIES=2

def now():
    return datetime.now(timezone.utc).isoformat()

def trial_id(z):
    if z.get('task')=='EVIDENCE_ABSENT_NEGATIVE_CONTROL':
        return z['case_id']+'|ABSENT'
    return f"{z['case_id']}|{z['treatment']}|{z['repeat']}"

def request_text(z):
    return canonical(z['request'])

def request_sha(z):
    return hashlib.sha256(request_text(z).encode('utf8')).hexdigest()

def checks_manifest(rows, expected_n, controls=False):
    assert len(rows)==expected_n, f'expected {expected_n}, got {len(rows)}'
    ids=[trial_id(z) for z in rows]
    assert len(set(ids))==len(ids),'duplicate trial ids'
    for z in rows:
        request=z['request']
        assert request['model']=='openai/gpt-oss-120b'
        assert request['max_tokens']==1600 and request['temperature']==0.2
        assert not set(request)-{'model','temperature','max_tokens','messages'}
        if not controls:
            assert z['treatment'] in ('T0','T1','T2','T3','T4')
            assert len(request['messages'])==(3 if z['treatment']=='T0' else 4)
            assert request['messages'][1]['role']=='system' and request['messages'][0]['role']=='system'
            assert hashlib.sha256(request['messages'][1]['content'].split('\n',1)[1].encode()).hexdigest()==z['trusted_sha256']
        else:
            assert z.get('task')=='EVIDENCE_ABSENT_NEGATIVE_CONTROL'
            assert len(request['messages'])==3
    if not controls:
        assert len({z['case_id'] for z in rows})==32
        assert {z['treatment'] for z in rows}=={'T0','T1','T2','T3','T4'}
        from collections import Counter
        assert set(Counter(z['case_id'] for z in rows).values())=={15}
    return ids

def json_verdict(payload):
    """Parse JSON output; no coercion of malformed replies to DEFER."""
    choices=payload.get('choices') or []
    message=choices[0].get('message',{}) if choices and isinstance(choices[0],dict) else {}
    content=message.get('content')
    if isinstance(content,list):
        content=''.join(c.get('text','') for c in content if isinstance(c,dict))
    if not isinstance(content,str) or not content.strip():
        return None,None,'empty_content'
    try:
        x=json.loads(content)
    except (TypeError,json.JSONDecodeError):
        return None,content,'invalid_json'
    if not isinstance(x,dict) or x.get('verdict') not in ('APPROVE','REJECT','DEFER'):
        return None,content,'invalid_verdict'
    if not isinstance(x.get('rationale'),str) or not x['rationale'].strip():
        return None,content,'missing_rationale'
    if not isinstance(x.get('cited_checks'),(list,dict)):
        return None,content,'missing_cited_checks'
    return x['verdict'],content,None

def read_done(path):
    rows=[]; seen={}
    if not path.exists(): return rows,seen
    for i,line in enumerate(path.read_text(encoding='utf8').splitlines(),1):
        if not line.strip():continue
        z=json.loads(line)
        if z['trial_id'] in seen:raise ValueError(f'duplicate terminal response for {z["trial_id"]}: line {i}')
        seen[z['trial_id']]=z
        rows.append(z)
    return rows,seen

def append_line(path,obj):
    path.parent.mkdir(parents=True,exist_ok=True)
    with open(path,'a',encoding='utf8') as f:
        f.write(canonical(obj)+'\n');f.flush();os.fsync(f.fileno())

def send_request(body,key,timeout):
    rq=Request(API_URL,data=body,method='POST',headers={
        'Authorization':'Bearer '+key,'Content-Type':'application/json',
        'HTTP-Referer':'https://colab.research.google.com',
        'X-Title':'FEMI-1 study'})
    try:
        with urlopen(rq,timeout=timeout) as f:
            raw=f.read()
            return int(f.status),json.loads(raw.decode('utf8'))
    except HTTPError as e:
        raw=e.read(3000).decode('utf8',errors='replace')
        return e.code,{'error':raw[:3000]}

def execute(rows,output,attempt_log,key,limit=None,pace=1.0,timeout=120):
    """Returns attempted terminal trials count; stored outputs are never simulated."""
    previous,done=read_done(output)
    known={trial_id(z):request_sha(z) for z in rows}
    for tid,z in done.items():
        if tid not in known or z['request_sha256']!=known[tid]:
            raise RuntimeError('Resume hash/inventory mismatch: '+tid)
    completed=0
    for i,z in enumerate(rows):
        tid=trial_id(z)
        if tid in done: continue
        if limit is not None and completed>=limit:break
        bytes_body=request_text(z).encode('utf8')
        digest=hashlib.sha256(bytes_body).hexdigest()
        last_result=None
        for attempt in range(TRANSPORT_MAX_RETRIES+1):
            start=time.perf_counter()
            status=None;payload=None;err=None
            try:
                status,payload=send_request(bytes_body,key,timeout)
            except (URLError,TimeoutError,ConnectionError,OSError,ValueError) as e:
                err=type(e).__name__+': '+str(e)[:500]
            latency=round(time.perf_counter()-start,3)
            retryable=(status in (408,409,425,429,500,502,503,504)) or (status is None)
            append_line(attempt_log,{'trial_id':tid,'request_sha256':digest,
                    'attempt':attempt,'timestamp_utc':now(),'http_status':status,
                    'elapsed_seconds':latency,'error':err,'retryable':retryable})
            last_result=(status,payload,err,latency)
            if status==200 and isinstance(payload,dict) and payload.get('choices'):
                break
            if not retryable:
                # Invalid parameter / model incompatibility: stop experiment, don't
                # silently change the protocol. Error row remains auditable.
                break
            if attempt<TRANSPORT_MAX_RETRIES:
                time.sleep(2**attempt+0.5)
        status,payload,err,latency=last_result
        success=(status==200 and isinstance(payload,dict) and bool(payload.get('choices')))
        verdict,content,parse_error=json_verdict(payload) if success else (None,None,'transport_failed')
        row={'trial_id':tid,'case_id':z['case_id'],'family':z['family'],'seed':z['seed'],
             'treatment':z['treatment'],'repeat':z.get('repeat'),
             'task':z.get('task','MAIN'),'request_sha256':digest,'trusted_sha256':z.get('trusted_sha256'),
             'timestamp_utc':now(),'http_status':status,'elapsed_seconds':latency,
             'response':payload if payload is not None else None,'transport_error':err,
             'parsed_verdict':verdict,'parse_error':parse_error,
             'usage':payload.get('usage') if isinstance(payload,dict) else None,
             'response_content':content}
        append_line(output,row)
        done[tid]=row
        completed+=1
        if not success and not (status in (408,409,425,429,500,502,503,504,None)):
            raise RuntimeError(f'Protocol/model incompatibility HTTP {status}; stop without changing model or request. Trial {tid}, response logged.')
        if completed%20==0:print(f'Terminal trials logged this run: {completed}; remaining: {len(rows)-len(done)}',flush=True)
        if pace and completed<len(rows):time.sleep(pace)
    return completed,len(done),len(rows)

def main():
    ap=argparse.ArgumentParser(description='Execute frozen FEMI-1 manifest on OpenRouter; no fake outputs')
    ap.add_argument('--manifest',required=True)
    ap.add_argument('--controls',required=True)
    ap.add_argument('--out',required=True,help='Directory for append-only logs')
    ap.add_argument('--live',action='store_true',help='Required to make billed API calls')
    ap.add_argument('--prereg-ref',default=None,help='Externally timestamped Git commit hash for the frozen protocol; required for --live')
    ap.add_argument('--max-new',type=int,default=None,help='For session chunking/resume, not adaptive sampling')
    ap.add_argument('--pace',type=float,default=1.0)
    ap.add_argument('--timeout',type=int,default=120)
    a=ap.parse_args()
    rows=load_jsonl(a.manifest);controls=load_jsonl(a.controls)
    checks_manifest(rows,480);checks_manifest(controls,8,True)
    out=Path(a.out);out.mkdir(parents=True,exist_ok=True)
    pre_ref=(a.prereg_ref or os.getenv('FEMI1_PREREG_REF') or '').strip()
    if a.live and not re.fullmatch(r'[0-9a-fA-F]{40,64}',pre_ref):
        raise RuntimeError('Before live FEMI-1 calls, publicly timestamp the frozen protocol/manifest; pass its Git commit SHA with --prereg-ref or FEMI1_PREREG_REF. Do not invent a hash.')
    metadata={
        'main_file_sha256':hashlib.sha256(Path(a.manifest).read_bytes()).hexdigest(),
        'control_file_sha256':hashlib.sha256(Path(a.controls).read_bytes()).hexdigest(),
        'prereg_ref':pre_ref if a.live else None,
        'note':'Source request JSON exactly as serialized in input manifest, not generated by live runner'}
    metadata_path=out/'manifest_sha256.json'
    if metadata_path.exists():
        previous=json.loads(metadata_path.read_text(encoding='utf8'))
        if previous['main_file_sha256']!=metadata['main_file_sha256'] or previous['control_file_sha256']!=metadata['control_file_sha256']:
            raise RuntimeError('Frozen request manifest changed since first session; refusing resume')
        if a.live and previous.get('prereg_ref') not in (None,pre_ref):
            raise RuntimeError('Externally timestamped preregistration ref changed; refusing resume')
    metadata_path.write_text(json.dumps(metadata,indent=2)+'\n',encoding='utf8')
    if not a.live:
        print('VALIDATED ONLY: 480 main and 8 control requests. No paid API calls.')
        return
    key=os.getenv('OPENROUTER_API_KEY') or os.getenv('HANDOFF_API_KEY')
    if not key:raise RuntimeError('OPENROUTER_API_KEY / HANDOFF_API_KEY not set: cannot make live OpenRouter calls')
    if a.max_new is not None and a.max_new<1:raise ValueError('--max-new must be >= 1')
    main_path=out/'main_responses.jsonl';control_path=out/'control_responses.jsonl'
    old_main,main_done=read_done(main_path)
    max_left=a.max_new
    if len(main_done)<480:
        n,now_n,total=execute(rows,main_path,out/'transport_attempts.jsonl',key,
                              limit=max_left,pace=a.pace,timeout=a.timeout)
        if max_left is not None:max_left-=n
    else:print('All 480 main trials already logged; resuming controls')
    new_main,main_done=read_done(main_path)
    if len(main_done)==480 and (max_left is None or max_left>0):
        execute(controls,control_path,out/'transport_attempts.jsonl',key,
                limit=max_left,pace=a.pace,timeout=a.timeout)
    print(f'Current completion: main {len(main_done)}/480, controls {len(read_done(control_path)[1])}/8')

if __name__=='__main__':main()
