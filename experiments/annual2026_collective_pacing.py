#!/usr/bin/env python3
"""Audited collective and report-required benchmarks; no result-based filtering."""
from pathlib import Path
from collections import Counter
import argparse, hashlib, json, os, random, statistics, subprocess, sys, time, re, signal
from concurrent.futures import ThreadPoolExecutor, as_completed

REPO=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(REPO))
from experiments.annual2026_tail_loads import fingerprint
from experiments.run_general_workloads import generate_trace
from experiments.summarize_workload import parse_fct, parse_config
from experiments.summarize_campaign import parse_guard_stats, parse_pfc, percentile, queue_summary_metrics

CASES=['incast2','incast7','mixed','fabric','alltoall256k','alltoall1m','alltoallv','ring1m','ring16m','concurrent']
TOPO='leaf_spine_16_100G_OS2'
COMMON={'lb':'fecmp','pfc':1,'irn':0,'bw':100,'topo':TOPO,'simul_time':.1,'netload':20,'buffer':9,'monitor_profile':'bulk','max_flows':25000,'analysis_warmup':0,'qlen_monitoring_interval':2000,'homa_resend_timeout_us':1000}
ARMS={'guard':{'cc':'guard'},'hpcc':{'cc':'hpcc'},'dcqcn':{'cc':'dcqcn'},'homa':{'cc':'homa'}}

def dump(path,value):
    path.parent.mkdir(parents=True,exist_ok=True)
    tmp=path.with_suffix(path.suffix+'.tmp');tmp.write_text(json.dumps(value,ensure_ascii=False,indent=2));tmp.replace(path)
def sha(path):return hashlib.sha256(Path(path).read_bytes()).hexdigest()

def generate(case,seed,root):
    folder=root/'inputs';folder.mkdir(parents=True,exist_ok=True)
    stem=f'{case}-{seed}';flow=folder/(stem+'.txt');dep=folder/(stem+'.deps');meta=folder/(stem+'.json')
    if meta.exists():
        data=json.loads(meta.read_text());assert sha(flow)==data['flow_sha256']
        if data['dependency_file']:assert sha(dep)==data['dependency_sha256']
        return data
    rng=random.Random(seed);flows=[];deps=[];operations=[]
    def add(src,dst,size,parents=(),release=2.001):
        i=len(flows);flows.append([src,dst,3,size,release]);deps.append(sorted(set(parents)));return i
    if case=='mixed':
        profile={'topo':TOPO,'hosts':16,'oversubscription':2,'simul_time':.02,'netload':20,'bw':100}
        generate_trace(REPO,'AliStorage2019',profile,seed,flow,3)
        lines=flow.read_text().splitlines();flows=[[int(x) for x in line.split()[:4]]+[float(line.split()[4])] for line in lines[1:]]
    elif case.startswith('incast') or case=='fabric':
        for turn in range(8):
            pairs=[(i,15) for i in range(8,8+int(case[6:]))] if case!='fabric' else [(i,i+8) for i in range(8)]
            for src,dst in pairs:add(src,dst,2*1024**2,release=2.001+turn*.002+rng.random()*.5e-6)
    else:
        placement=list(range(16));rng.shuffle(placement)
        def alltoall(job,size,variable=False):
            previous=[]
            for iteration in range(2):
                ids=[]
                for src in placement:
                    destinations=[d for d in placement if d!=src]
                    weights=[8 if variable and d==placement[0] else 1 for d in destinations]
                    sizes=[size*15*w//sum(weights) for w in weights];sizes[-1]+=size*15-sum(sizes)
                    for dst,amount in zip(destinations,sizes):
                        ids.append(add(src,dst,amount,previous,2.001+(rng.random()*.5e-6 if iteration==0 else 0)))
                operations.append({'name':f'{job}-{iteration}','kind':'alltoallv' if variable else 'alltoall','flows':ids,'roots':ids,'terminals':ids,'payload_bytes_per_rank':size*15})
                previous=ids
        def ring(job,tensor):
            previous=[];chunk=tensor//16
            for iteration in range(2):
                ids=[];stages=[]
                for step in range(30):
                    stage=[]
                    for rank,src in enumerate(placement):
                        parents=previous if step==0 else [stages[-1][rank],stages[-1][(rank-1)%16]]
                        stage.append(add(src,placement[(rank+1)%16],chunk,parents,2.001+(rng.random()*.5e-6 if iteration==0 and step==0 else 0)))
                    stages.append(stage);ids+=stage
                operations.append({'name':f'{job}-{iteration}','kind':'ring_allreduce','flows':ids,'roots':stages[0],'terminals':stages[-1],'tensor_bytes_per_rank':tensor,'steps':30})
                previous=stages[-1]
        if case.startswith('alltoall'):alltoall('exchange',1024**2 if case=='alltoall1m' else 256*1024,case=='alltoallv')
        elif case.startswith('ring'):ring('reduction',1024**2 if case=='ring1m' else 16*1024**2)
        elif case=='concurrent':
            ring('reduction',8*1024**2);alltoall('exchange',256*1024)
        else:raise ValueError(case)
    is_dag=bool(operations)
    if case!='mixed':
        order=sorted(range(len(flows)),key=lambda i:(flows[i][4],i));mapping={old:new for new,old in enumerate(order)}
        flows=[flows[i] for i in order]
        deps=[[mapping[j] for j in deps[i]] for i in order]
        for op in operations:
            for key in ['flows','roots','terminals']:op[key]=[mapping[i] for i in op[key]]
        flow.write_text(str(len(flows))+'\n'+''.join(f'{s} {d} {p} {b} {t:.9f}\n' for s,d,p,b,t in flows))
    if is_dag:dep.write_text(str(len(flows))+'\n'+''.join(f'{i} {len(parents)}'+(' '+' '.join(map(str,parents)) if parents else '')+'\n' for i,parents in enumerate(deps)))
    data={'case':case,'seed':seed,'flow_file':str(flow),'dependency_file':str(dep) if is_dag else None,'flow_sha256':sha(flow),'dependency_sha256':sha(dep) if is_dag else None,'flows':flows,'dependencies':deps if is_dag else [],'operations':operations,'flow_count':len(flows),'total_bytes':sum(row[3] for row in flows)}
    dump(meta,data);return data

def summarize(out,trace):
    sid=out.name;fct=parse_fct(out/f'{sid}_out_fct.txt')
    assert len(fct)==trace['flow_count']
    assert Counter((r['src'],r['dst'],r['size']) for r in fct)==Counter((f[0],f[1],f[3]) for f in trace['flows'])
    ops=[]
    if trace['dependency_file']:
        lines=(out/f'{sid}_out_fct.txt.dag.tsv').read_text().splitlines()[1:]
        rows={}
        for line in lines:
            values=list(map(int,line.split()));i,src,dst,size,release,start,finish=values
            assert i not in rows and (src,dst,size)==tuple(trace['flows'][i][k] for k in [0,1,3])
            assert start>=release and finish>=start
            rows[i]={'start':start,'finish':finish,'src':src,'dst':dst,'size':size}
        assert set(rows)==set(range(trace['flow_count']))
        assert Counter((r['src'],r['dst'],r['size'],r['start_ns'],r['finish_ns']) for r in fct)==Counter((r['src'],r['dst'],r['size'],r['start'],r['finish']) for r in rows.values())
        for i,parents in enumerate(trace['dependencies']):
            assert all(rows[i]['start']>=rows[p]['finish'] for p in parents),(i,parents)
        for op in trace['operations']:
            start=min(rows[i]['start'] for i in op['roots']);finish=max(rows[i]['finish'] for i in op['terminals'])
            ops.append({'name':op['name'],'kind':op['kind'],'cct_us':(finish-start)/1000,'start_ns':start,'finish_ns':finish})
    else:
        expected=Counter((f[0],f[1],f[3],round(f[4]*1e9)) for f in trace['flows'])
        for r in fct:
            matches=[(r['src'],r['dst'],r['size'],r['start_ns']+d) for d in [-2,-1,0,1,2]]
            k=next((k for k in matches if expected[k]>0),None);assert k is not None
            expected[k]-=1
        assert not any(expected.values())
    selected=[r for r in fct if trace['case']!='mixed' or r['start_ns']>2005000000]
    vals=[r['fct_us'] for r in selected]
    metrics={'mean_fct_us':statistics.fmean(vals),'p99_fct_us':percentile(vals,99),'makespan_us':(max(r['finish_ns'] for r in fct)-min(r['start_ns'] for r in fct))/1000}
    if ops:metrics['mean_cct_us']=statistics.fmean(r['cct_us'] for r in ops)
    metrics.update({k:v for k,scope,v,n in queue_summary_metrics(out/f'{sid}_out_queue_stats.txt')})
    return {'metrics':metrics,'operations':ops,'stats':parse_guard_stats(out/f'{sid}_out_guard_stats.txt'),'pfc':parse_pfc(out/f'{sid}_out_pfc.txt'),'completed':len(fct),'analyzed':len(selected),'integrity':'all flow identities and dependency edges checked','output_hashes':{p.name:sha(p) for p in out.iterdir() if p.is_file()}}

def main():
    parser=argparse.ArgumentParser();parser.add_argument('--root',type=Path,required=True);parser.add_argument('--seeds',default='1101');parser.add_argument('--cases',default=','.join(CASES));parser.add_argument('--arms',default='guard,hpcc,dcqcn,homa');parser.add_argument('--variants',type=Path);parser.add_argument('--jobs',type=int,default=4);parser.add_argument('--prepare-only',action='store_true');a=parser.parse_args()
    assert 1<=a.jobs<=8
    runtime=fingerprint()
    root=a.root.resolve();root.mkdir(parents=True,exist_ok=True);os.environ['PATH']='/home/gengjiayao/.pyenv/versions/2.7.18/bin:'+os.environ['PATH']
    variants=json.loads(a.variants.read_text()) if a.variants else ARMS
    cases=a.cases.split(',');seeds=list(map(int,a.seeds.split(',')));arms=a.arms.split(',')
    traces=[generate(c,s,root) for c in cases for s in seeds]
    revision=subprocess.check_output(['git','rev-parse','HEAD'],cwd=REPO,text=True).strip()
    plan={'cases':cases,'seeds':seeds,'arms':{k:variants[k] for k in arms},'common':COMMON,'git':revision,'source_diff_sha256':hashlib.sha256(subprocess.check_output(['git','diff'],cwd=REPO)).hexdigest(),'binary_sha256':sha(REPO/'build/scratch/network-load-balance'),'runtime':runtime,'runner_sha256':sha(__file__),'jobs':a.jobs,'inputs':[{'case':t['case'],'seed':t['seed'],'flow_sha256':t['flow_sha256'],'dependency_sha256':t['dependency_sha256']} for t in traces],'primary_metric':'P99 FCT for required cases, mean per-iteration CCT for collectives, total makespan for concurrent jobs','policy':'Keep every run, seed, slow flow and failure. Fixed shared topology, routing and workload graph. Source/destination mapping and operation dependencies are identical for every algorithm. No GPU compute time is modeled.'}
    if (root/'plan.json').exists():assert json.loads((root/'plan.json').read_text())==plan,'frozen campaign changed'
    else:dump(root/'plan.json',plan)
    if a.prepare_only:print('Prepared',len(traces),'inputs');return
    def execute(trace,arm):
            key=f'{trace["case"]}-{trace["seed"]}-{arm}';folder=root/'runs'/key;folder.mkdir(parents=True,exist_ok=True);record=folder/'result.json'
            if record.exists():
                old=json.loads(record.read_text());assert old['status']=='completed','previous failure preserved';return old
            params={**COMMON,**variants[arm],'no_build':1,'flow_file':trace['flow_file'],'seed':trace['seed']}
            if trace['dependency_file']:params['flow_dependencies']=trace['dependency_file']
            command=[sys.executable,'run.py']
            for k,v in params.items():command+=['--'+k,str(v)]
            result={'key':key,'case':trace['case'],'seed':trace['seed'],'arm':arm,'command':command,'params':params,'git':revision,'binary_sha256':plan['binary_sha256'],'input_sha256':trace['flow_sha256'],'dependency_sha256':trace['dependency_sha256'],'status':'running','started_utc':time.strftime('%Y-%m-%dT%H:%M:%SZ',time.gmtime())}
            dump(folder/'manifest.json',result);started=time.monotonic()
            try:
                assert fingerprint()==runtime
                with (folder/'driver.log').open('w') as log:
                    proc=subprocess.Popen(command,cwd=REPO,stdout=log,stderr=subprocess.STDOUT,start_new_session=True)
                    try:proc.wait(timeout=600)
                    except subprocess.TimeoutExpired:
                        os.killpg(proc.pid,signal.SIGTERM);proc.wait();raise
                result['exit_code']=proc.returncode
                paths=re.findall(r'The new directory is created  - (.+)/',(folder/'driver.log').read_text())
                assert len(paths)==1,paths
                out=Path(paths[0]);result['output_dir']=str(out)
                assert fingerprint()==runtime
                assert proc.returncode==0,'run failed; see logs'
                assert sha(REPO/'build/scratch/network-load-balance')==plan['binary_sha256'],'binary changed during campaign'
                assert sha(out/f'{out.name}_input_flow.txt')==trace['flow_sha256']
                if trace['dependency_file']:assert sha(out/f'{out.name}_input_dependencies.txt')==trace['dependency_sha256']
                result.update(summarize(out,trace));result['status']='completed'
            except Exception as e:
                result['status']='failed';result['error']=repr(e)
            result['wall_seconds']=time.monotonic()-started;dump(record,result)
            return result
    completed=[]
    with ThreadPoolExecutor(max_workers=a.jobs) as pool:
        futures=[pool.submit(execute,t,arm) for t in traces for arm in arms]
        for f in as_completed(futures):
            result=f.result();completed.append(result);completed.sort(key=lambda r:r['key']);dump(root/'results.json',completed)
            print(json.dumps({k:result.get(k) for k in ['key','status','metrics','wall_seconds','error']},ensure_ascii=False),flush=True)
    assert all(r['status']=='completed' for r in completed),'failure records preserved'
    print('COMPLETE',len(completed),flush=True)

if __name__=='__main__':main()
