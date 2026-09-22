"""Frozen, resumable remeasurement. No old measurements are consumed."""
import argparse
from concurrent.futures import ThreadPoolExecutor, as_completed
import hashlib
import json
import os
from pathlib import Path
import random
import subprocess
import sys
import time

ROOT = Path(__file__).resolve().parents[1]
REPO = Path('/home/gengjiayao/ict/guard')
ARMS = ['guard', 'hpcc', 'homa', 'dcqcn', 'timely']
SEEDS = [301, 302, 303, 304, 305]
def sha(p):
    h = hashlib.sha256()
    with open(p, 'rb') as f:
        for b in iter(lambda: f.read(1048576), b''): h.update(b)
    return h.hexdigest()
def save(p, x):
    p = Path(p)
    tmp = p.with_suffix(p.suffix + '.tmp')
    tmp.write_text(json.dumps(x, indent=2) + '\n')
    tmp.replace(p)
def flow_file(p, rows):
    rows.sort(key=lambda x: x[4])
    p.write_text(str(len(rows)) + '\n' + ''.join('%d %d %d %d %.9f\n' % tuple(x) for x in rows))

def prepare():
    if (ROOT/'manifest.json').exists():
        raise RuntimeError('Manifest already frozen; use run/resume.')
    (ROOT/'flows').mkdir(exist_ok=True)
    tasks = []
    for seed in SEEDS:
        for name, cdf, hosts, load in [('ali30','AliStorage2019',128,30), ('ali50','AliStorage2019',128,50), ('web40','WebSearch',16,40), ('fb40','FbHdp2015',16,40)]:
            f = ROOT/'flows'/f'{name}-s{seed}.txt'
            command = [sys.executable,str(REPO/'traffic_gen/traffic_gen.py'),'-c',str(REPO/'traffic_gen'/f'{cdf}.txt'),'-n',str(hosts),'-l',str(load/100),'-b','100G','-t','0.01','-s',str(seed),'-o',str(f)]
            subprocess.run(command,check=True,stdout=subprocess.DEVNULL)
            arms = ARMS + (['no_oflm','no_selective','no_release'] if name=='ali50' else [])
            for arm in arms:
                extra={}
                if arm in ['no_oflm','no_selective']: extra['guard_selective_registration']=0
                if arm in ['no_oflm','no_release']: extra['guard_proactive_release']=0
                tasks.append(dict(study=name,seed=seed,arm=arm,cc=arm if arm in ARMS else 'guard',flow=str(f),topo=f'leaf_spine_{hosts}_100G_OS1',duration=0.01,warmup=0.005,load=load,cdf=cdf,extra=extra,monitor='bulk',buffer=9))
        for name in ['fabric','receiver','hybrid','fairness','alltoall','ring','allreduce_dp2']:
            rng=random.Random(seed)
            j=lambda: rng.uniform(0,0.5e-6)
            topo='leaf_spine_16_100G_OS1'
            duration=.02
            if name=='fabric':
                topo='leaf_spine_8_100G_OS4'
                rows=[(i,i+4,3,8*1048576,2.001+j()) for i in range(4)]
            elif name=='receiver':
                rows=[(i,15,3,8*1048576,2.001+j()) for i in range(4)]
            elif name=='hybrid':
                topo='leaf_spine_8_100G_OS4'
                rows=[(s,d,3,8*1048576,2.001+j()) for s,d in [(0,5),(1,5),(2,6),(3,7),(4,5)]]
            elif name=='fairness':
                duration=.1
                rows=[(i,15,3,150000000,2+i*.003+j()) for i in range(4)]
            elif name=='alltoall':
                rows=[(s,d,3,524288,2.001+j()) for s in range(16) for d in range(16) if s!=d]
            elif name=='ring':
                topo='leaf_spine_16_100G_OS4'
                ring=[v for pair in zip(range(8),range(8,16)) for v in pair]
                rows=[(s,ring[(i+1)%16],3,524288,2+.004*(step+1)/31+j()) for step in range(30) for i,s in enumerate(ring)]
            else:
                # Preserve the old 16-host DP=2, 2 GB/host, 25 MB bucket geometry.
                # Injection is open-loop: report communication trace span, never training JCT.
                duration=.25
                rows=[(s,(s+8)%16,3,25000000,2.001+bucket*.0025+j()) for bucket in range(80) for s in range(16)]
            f=ROOT/'flows'/f'{name}-s{seed}.txt'
            flow_file(f,rows)
            arms=ARMS + (['receiver_only','keep_last_hop','lambda1','lambda14'] if name in ['fabric','receiver','hybrid'] else [])
            for arm in arms:
                extra={}
                if arm=='keep_last_hop': extra['guard_keep_last_hop_int']=1
                if arm=='lambda1': extra['guard_lambda']=1
                if arm=='lambda14': extra['guard_lambda']=1.4
                cc=arm if arm in ARMS else ('guard-active-only' if arm=='receiver_only' else 'guard')
                tasks.append(dict(study=name,seed=seed,arm=arm,cc=cc,flow=str(f),topo=topo,duration=duration,warmup=0,load=40,cdf='AliStorage2019',extra=extra,monitor='full' if name=='fairness' else 'bulk',buffer=32 if name=='ring' else 16))
    for t in tasks:
        t['key']=f"{t['study']}-s{t['seed']}-{t['arm']}"
        t['flow_sha256']=sha(t['flow'])
        t['flow_count']=int(Path(t['flow']).read_text().splitlines()[0])
    provenance=dict(created_utc=time.strftime('%Y-%m-%dT%H:%M:%SZ',time.gmtime()),git_sha=subprocess.check_output(['git','rev-parse','HEAD'],cwd=REPO,text=True).strip(),binary_sha256=sha(REPO/'build/scratch/network-load-balance'),run_py_sha256=sha(REPO/'run.py'),seeds=SEEDS,profile='Current run.py defaults, explicitly frozen in every generated config; no V19--V35 optional policy enabled.',tasks=tasks)
    save(ROOT/'manifest.json',provenance)
    print('FROZEN',len(tasks),'runs',flush=True)

def run_one(t):
    d=ROOT/'runs'/t['key']; d.mkdir(exist_ok=True)
    if (d/'result.json').exists(): return json.loads((d/'result.json').read_text())
    assert sha(t['flow'])==t['flow_sha256']
    rec=dict(t,started_utc=time.strftime('%Y-%m-%dT%H:%M:%SZ',time.gmtime()))
    cmd=[sys.executable,str(ROOT/'scripts/config_only.py'),'--cc',t['cc'],'--lb','fecmp','--pfc','1','--irn','0','--topo',t['topo'],'--simul_time',str(t['duration']),'--analysis_warmup',str(t['warmup']),'--flow_file',t['flow'],'--max_flows','500000','--netload',str(t['load']),'--cdf',t['cdf'],'--seed',str(t['seed']),'--monitor_profile',t['monitor'],'--buffer',str(t['buffer'])]
    if t['monitor']=='full': cmd += ['--qlen_monitoring_interval','10000','--sw_monitoring_interval','10000']
    for k,v in t['extra'].items(): cmd += ['--'+k,str(v)]
    rec['driver_command']=cmd
    start=time.monotonic()
    try:
        cp=subprocess.run(cmd,cwd=REPO,text=True,stdout=subprocess.PIPE,stderr=subprocess.STDOUT,timeout=120)
        (d/'config-generation.log').write_text(cp.stdout)
        if cp.returncode: raise RuntimeError('config generation failed')
        config=REPO/next(l.split('=',1)[1] for l in cp.stdout.splitlines() if l.startswith('CONFIG_READY='))
        rec['config']=str(config); rec['config_sha256']=sha(config)
        rec['output_dir']=str(config.parent)
        (d/'output').symlink_to(config.parent,target_is_directory=True) if not (d/'output').exists() else None
        save(d/'running.json',rec)
        env=dict(os.environ,LD_LIBRARY_PATH=str(REPO/'build'))
        with (d/'simulation.log').open('w') as log:
            result=subprocess.run([str(REPO/'build/scratch/network-load-balance'),str(config)],cwd=REPO,env=env,stdout=log,stderr=subprocess.STDOUT,timeout=7200)
        rec['returncode']=result.returncode
        fcts=list(config.parent.glob('*_out_fct.txt'))
        rec['completed']=sum(1 for _ in fcts[0].open()) if fcts else 0
        rec['status']='completed' if result.returncode==0 and rec['completed']==t['flow_count'] else 'incomplete_or_failed'
    except Exception as e:
        rec['status']='error'; rec['error']=repr(e)
    rec['wall_seconds']=time.monotonic()-start
    save(d/'result.json',rec)
    print(rec['status'],t['key'],round(rec['wall_seconds'],1),rec.get('completed'),flush=True)
    return rec

def main():
    p=argparse.ArgumentParser();p.add_argument('mode',choices=['prepare','run']);p.add_argument('--workers',type=int,default=6);p.add_argument('--studies',nargs='*');p.add_argument('--seeds',nargs='*',type=int);p.add_argument('--arms',nargs='*');a=p.parse_args()
    if a.mode=='prepare': return prepare()
    m=json.loads((ROOT/'manifest.json').read_text())
    assert sha(REPO/'build/scratch/network-load-balance')==m['binary_sha256']
    tasks=[t for t in m['tasks'] if (not a.studies or t['study'] in a.studies) and (not a.seeds or t['seed'] in a.seeds) and (not a.arms or t['arm'] in a.arms)]
    with ThreadPoolExecutor(max_workers=a.workers) as pool:
        for f in as_completed([pool.submit(run_one,t) for t in tasks]): f.result()
if __name__=='__main__':main()
