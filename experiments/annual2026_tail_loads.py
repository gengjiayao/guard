#!/usr/bin/env python3
"""Tail-first workload benchmark. Preserves all flows, runs, and runtime hashes."""
from pathlib import Path
from collections import Counter
import argparse, hashlib, json, os, statistics, subprocess, sys, time
REPO=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(REPO))
from experiments.annual2026_collectives import dump,sha,COMMON,summarize
from experiments.run_general_workloads import generate_trace
from experiments.summarize_workload import parse_fct
from experiments.summarize_campaign import percentile

def fingerprint():
    paths=[REPO/'build/scratch/network-load-balance',*sorted((REPO/'build').glob('*.so'))]
    return {str(p.relative_to(REPO)):sha(p) for p in paths}

def generate(cdf,load,seed,duration,root):
    case=f'{cdf}-L{load}';flow=root/'inputs'/f'{case}-{seed}.txt';meta=flow.with_suffix('.json')
    flow.parent.mkdir(parents=True,exist_ok=True)
    if meta.exists():
        t=json.loads(meta.read_text());assert sha(flow)==t['flow_sha256'];return t
    generate_trace(REPO,cdf,{'topo':COMMON['topo'],'hosts':16,'oversubscription':2,'simul_time':duration,'netload':load*2,'bw':100},seed,flow,3)
    flows=[[int(x) for x in l.split()[:4]]+[float(l.split()[4])] for l in flow.read_text().splitlines()[1:]]
    t={'case':case,'cdf':cdf,'load':load,'seed':seed,'duration':duration,'flow_file':str(flow),'flow_sha256':sha(flow),'dependency_file':None,'dependency_sha256':None,'flows':flows,'flow_count':len(flows),'total_bytes':sum(f[3] for f in flows),'operations':[],'dependencies':[]}
    dump(meta,t);return t

def tail_metrics(out,warmup):
    rows=parse_fct(out/f'{out.name}_out_fct.txt');rows=[r for r in rows if r['start_ns']>=2e9+warmup*1e9]
    groups={'all':rows,**{n:[r for r in rows if lo<r['size']<=hi] for n,lo,hi in [('le8KiB',0,8192),('8to64KiB',8192,65536),('64KiBto1MiB',65536,1048576),('gt1MiB',1048576,float('inf'))]}}
    return {k:{'n':len(g),**{f'p{q}_fct_us':percentile([r['fct_us'] for r in g],q) for q in [95,99]},'mean_fct_us':statistics.fmean(r['fct_us'] for r in g)} for k,g in groups.items() if g}

def main():
    p=argparse.ArgumentParser();p.add_argument('--root',type=Path,required=True);p.add_argument('--variants',type=Path,required=True);p.add_argument('--arms',default='guard,homa');p.add_argument('--seeds',default='2101');p.add_argument('--loads',default='20,50,70');p.add_argument('--cdfs',default='AliStorage2019,WebSearch');p.add_argument('--ali-duration',type=float,default=.02);p.add_argument('--web-duration',type=float,default=.06);p.add_argument('--warmup-fraction',type=float,default=.25);p.add_argument('--prepare-only',action='store_true');a=p.parse_args()
    root=a.root.resolve();root.mkdir(parents=True,exist_ok=True);os.environ['PATH']='/home/gengjiayao/.pyenv/versions/2.7.18/bin:'+os.environ['PATH']
    variants=json.loads(a.variants.read_text());arms=a.arms.split(',');seeds=list(map(int,a.seeds.split(',')))
    traces=[generate(c,l,s,a.ali_duration if c=='AliStorage2019' else a.web_duration,root) for c in a.cdfs.split(',') for l in map(int,a.loads.split(',')) for s in seeds]
    revision=subprocess.check_output(['git','rev-parse','HEAD'],cwd=REPO,text=True).strip();runtime=fingerprint()
    plan={'git':revision,'source_diff_sha256':hashlib.sha256(subprocess.check_output(['git','diff'],cwd=REPO)).hexdigest(),'runner_sha256':sha(__file__),'runtime':runtime,'common':COMMON,'variants':{k:variants[k] for k in arms},'seeds':seeds,'warmup_fraction':a.warmup_fraction,'inputs':[{k:t[k] for k in ['case','seed','cdf','load','duration','flow_count','flow_sha256']} for t in traces],'cdf_hashes':{c:sha(REPO/'traffic_gen'/f'{c}.txt') for c in a.cdfs.split(',')},'primary':'Per-seed P99 FCT, all flow sizes; P95 and size bins are secondary. Compute paired improvement, never pool seeds.','policy':'All runs and failures preserved; all input flows must complete, no completion-window censoring; fixed start-time warmup. Identical traces, topology, routing, and physical capacity. Homa derives priorities from same complete input snapshot.','reserved_holdout_seeds':[3101,3102,3103,3104,3105]}
    if (root/'plan.json').exists():assert json.loads((root/'plan.json').read_text())==plan,'frozen plan changed'
    else:dump(root/'plan.json',plan)
    if a.prepare_only:return
    done=[]
    for t in traces:
      for arm in arms:
        key=f'{t["case"]}-{t["seed"]}-{arm}';folder=root/'runs'/key;folder.mkdir(parents=True,exist_ok=True);record=folder/'result.json'
        if record.exists():
            old=json.loads(record.read_text());assert old['status']=='completed';done.append(old);continue
        params={**COMMON,**variants[arm],'flow_file':t['flow_file'],'cdf':t['cdf'],'seed':t['seed'],'netload':t['load']*2,'simul_time':max(.1,t['duration']+.05),'max_flows':1000000}
        command=[sys.executable,'run.py'];[command.extend(['--'+k,str(v)]) for k,v in params.items()]
        before=set((REPO/'mix/output').iterdir());r={'key':key,'case':t['case'],'seed':t['seed'],'arm':arm,'params':params,'command':command,'git':revision,'input_sha256':t['flow_sha256'],'status':'running'};dump(folder/'manifest.json',r);start=time.monotonic()
        try:
            assert fingerprint()==runtime
            with (folder/'driver.log').open('w') as f:proc=subprocess.run(command,cwd=REPO,stdout=f,stderr=subprocess.STDOUT,timeout=1800)
            fresh=set((REPO/'mix/output').iterdir())-before;assert len(fresh)==1
            out=fresh.pop();r['output_dir']=str(out);r['exit_code']=proc.returncode
            assert proc.returncode==0;assert fingerprint()==runtime;assert sha(out/f'{out.name}_input_flow.txt')==t['flow_sha256']
            r.update(summarize(out,t));r['tails']=tail_metrics(out,t['duration']*a.warmup_fraction);r['status']='completed'
        except Exception as e:r['status']='failed';r['error']=repr(e)
        r['wall_seconds']=time.monotonic()-start;dump(record,r);done.append(r);dump(root/'results.json',done)
        print(json.dumps({k:r.get(k) for k in ['key','status','tails','wall_seconds','error']}),flush=True)
        if r['status']!='completed':raise RuntimeError(r['error'])
    print('COMPLETE',len(done),flush=True)
if __name__=='__main__':main()
