"""Validate flow identity and produce seed-level metrics from fresh raw runs."""
from collections import defaultdict
from fractions import Fraction
import csv
import hashlib
import json
from pathlib import Path
import sys
import numpy as np

ROOT=Path(__file__).resolve().parents[1]
REPO=Path('/home/gengjiayao/ict/guard')
sys.path.insert(0,str(REPO))
from experiments.summarize_campaign import parse_guard_stats,parse_port_queue_summaries,parse_pfc
sys.path.insert(0,str(ROOT/'scripts'))
from campaign import sha,save

BINS=[0,4000,8000,16000,32000,64000,128000,256000,2000000,float('inf')]
def validate_identity(t,a):
    inp=np.loadtxt(t['flow'],skiprows=1,ndmin=2)
    exp=np.column_stack([inp[:,0],inp[:,1],inp[:,3],np.rint(inp[:,4]*1e9)]).astype(np.int64)
    got=a[:,[0,1,4,5]]
    if len(exp)!=len(got): raise ValueError('Missing/extra completions')
    exp=exp[np.lexsort(exp.T[::-1])];got=got[np.lexsort(got.T[::-1])]
    if not np.array_equal(exp[:,:3],got[:,:3]): raise ValueError('Endpoint/size mismatch')
    if np.max(np.abs(exp[:,3]-got[:,3]))>2: raise ValueError('Start-time mismatch >2 ns')
    if np.any(a[:,6:]<=0): raise ValueError('Nonpositive FCT/ideal')
    if len(np.unique(a[:,:6],axis=0))!=len(a): raise ValueError('Duplicate completion')
    return hashlib.sha256(got.tobytes()).hexdigest()

def summarize(r):
    d=Path(r['output_dir']); out=ROOT/'runs'/r['key']/'metrics.json'
    if r['status']!='completed':return None
    fct=next(d.glob('*_out_fct.txt'))
    if sha(r['flow'])!=r['flow_sha256']:raise ValueError('Input changed')
    if sha(r['config'])!=r['config_sha256']:raise ValueError('Configuration changed')
    cache_provenance={
        'analysis':sha(Path(__file__)),
        'parser':sha(REPO/'experiments/summarize_campaign.py'),
        'result':hashlib.sha256(json.dumps(r,sort_keys=True).encode()).hexdigest(),
        'files':{f.name:sha(f) for pat in ['*_out_fct.txt','*_out_guard_stats.txt','*_out_queue_stats.txt','*_out_pfc.txt'] for f in d.glob(pat)}}
    if out.exists():
        cached=json.loads(out.read_text())
        if cached.get('cache_provenance')==cache_provenance:return cached
    a=np.loadtxt(fct,dtype=np.int64,ndmin=2)
    identity=validate_identity(r,a)
    stats_path=next(d.glob('*_out_guard_stats.txt'))
    stats=parse_guard_stats(stats_path)
    dcqcn_headers=None
    for line in stats_path.read_text().splitlines():
        v=line.split()
        if v[:2]==['dcqcn','node']:dcqcn_headers=v[2:]
        if v[:1]==['dcqcn_total']:
            stats['dcqcn_total_values']=list(map(int,v[1:]))
    queue_path=next(d.glob('*_out_queue_stats.txt'))
    ports=parse_port_queue_summaries(queue_path)
    queue={}
    for line in queue_path.read_text().splitlines():
        x=line.split()
        if len(x)==2:queue[x[0]]=float(x[1])
    pfc_path=next(d.glob('*_out_pfc.txt'))
    pfc=parse_pfc(pfc_path)
    selected=a[a[:,5]>int((2+r['warmup'])*1e9)]
    # Retain every completion after warmup: no protocol-dependent finish cutoff.
    durations=selected[:,6]/1000
    slows=np.maximum(1,selected[:,6]/selected[:,7])
    span=(a[:,5]+a[:,6]).max()-a[:,5].min()
    metrics={'fct_mean_us':float(np.mean(durations)),'slowdown_mean':float(np.mean(slows)),
             'span_ms':float(span/1e6),'goodput_gbps':float(a[:,4].sum()*8/span),
             'mean_flow_goodput_gbps':float(np.mean(selected[:,4]*8/selected[:,6])),
             'completion_fraction':len(a)/r['flow_count'],'eligible_flows':len(selected),
             'queue_mean_kb':queue['average_bytes']/1000,
             'queue_max_kb':queue['max_bytes']/1000}
    for q in [50,95,99,99.9]:
        tag=str(q).replace('.','_')
        metrics['fct_p'+tag+'_us']=float(np.percentile(durations,q))
        metrics['slowdown_p'+tag]=float(np.percentile(slows,q))
    # The simulator stops soon after the last completion. Pad the unused part
    # of a frozen observation window with zero queue, avoiding a varying denominator.
    interval=r['extra'].get('qlen_monitoring_interval',10000 if r['monitor']=='full' else 1000)
    config_values={v[0]:v[1] for line in Path(r['config']).read_text().splitlines() if len(v:=line.split())>=2}
    # ns-3 converts the parsed binary double to fixed point and truncates ns.
    # E.g. Seconds(2.01) is 2,009,999,999 ns, not 2,010,000,000 ns.
    start_ns=int(Fraction.from_float(float(config_values['QLEN_MON_START']))*10**9)
    end_ns=int(Fraction.from_float(float(config_values['QLEN_MON_END']))*10**9)
    planned=(end_ns-start_ns)//interval+1
    if any(p['samples']>planned for p in ports):raise ValueError('Queue samples exceed observation window')
    metrics['queue_planned_samples_per_port']=planned
    metrics['queue_fixed_mean_kb']=sum(p['average_bytes']*p['samples'] for p in ports)/(len(ports)*planned)/1000
    for p in ports:
        p['fixed_average_bytes']=p['average_bytes']*p['samples']/planned
    metrics['queue_worst_port_fixed_mean_us']=max(p['fixed_average_bytes'] for p in ports)*8/100000
    metrics['queue_p99_kb']=queue['p99_bytes']/1000
    metrics['drops']=int(stats['switch_drops_total'])
    metrics['recovery_nacks']=int(stats['recovery_nacks_generated'])
    metrics['timeout_recoveries']=int(stats['timeout_recoveries'])
    metrics['grants']=int(stats['grants_sent'])
    metrics['grant_kbytes']=int(stats['grant_bytes_sent'])/1000
    metrics['hpcc_changes']=int(stats['hpcc_actual_rate_changes'])
    metrics['receiver_bindings']=int(stats['grant_binding_updates'])
    metrics['fabric_bindings']=int(stats['reactive_binding_updates'])
    if isinstance(pfc,dict):
        for k,v in pfc.items():
            if isinstance(v,(int,float)):metrics[k]=v
    bins=[]
    for lo,hi in zip(BINS[:-1],BINS[1:]):
        b=slows[(selected[:,4]>lo)&(selected[:,4]<=hi)]
        bins.append({'lo':lo,'hi':hi if np.isfinite(hi) else None,'n':len(b),
                     'mean':float(np.mean(b)) if len(b) else None,
                     **{str(q):float(np.percentile(b,q)) if len(b) else None for q in [95,99,99.9]}})
    rec={'key':r['key'],'study':r['study'],'arm':r['arm'],'seed':r['seed'],'flow_sha256':r['flow_sha256'],
         'completion_identity_sha256':identity,'fct_sha256':sha(fct),'stats_sha256':sha(stats_path),
         'queue_sha256':sha(queue_path),'metrics':metrics,'stats':stats,'ports':ports,'bins':bins,
         'cache_provenance':cache_provenance,'valid':True,'lossless':metrics['drops']==0,'output_dir':str(d),'fct_file':str(fct)}
    save(out,rec)
    return rec

def main():
    rows=[];failures=[]
    for p in sorted((ROOT/'runs').glob('*/result.json')):
        r=json.loads(p.read_text())
        try:
            row=summarize(r)
            if row: rows.append(row)
            else: failures.append({'key':r['key'],'status':r['status']})
        except Exception as e:failures.append({'key':r['key'],'error':repr(e)})
    hashes=defaultdict(set)
    for r in rows:hashes[(r['study'],r['seed'])].add((r['flow_sha256'],r['completion_identity_sha256']))
    for key,v in hashes.items():
        if len(v)!=1:failures.append({'key':str(key),'error':'cross-arm identity mismatch'})
    save(ROOT/'analysis.json',{'runs':rows,'failures':failures})
    names=sorted(set(k for r in rows for k in r['metrics']))
    with (ROOT/'metrics.csv').open('w') as f:
        w=csv.DictWriter(f,fieldnames=['study','arm','seed']+names);w.writeheader()
        for r in rows:w.writerow({k:r[k] for k in ['study','arm','seed']}|r['metrics'])
    print('Validated',len(rows),'runs; failures',json.dumps(failures))
if __name__=='__main__':main()
