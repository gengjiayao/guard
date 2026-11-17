from pathlib import Path
from collections import defaultdict
import csv,hashlib,json,math,statistics,sys,tarfile,time
work=Path('/home/gengjiayao/ict/guard-joint-20261117');original=Path('/home/gengjiayao/ict/guard-fixed-reference-20261117')
sys.path.insert(0,str(work))
from experiments.annual2026_collectives import summarize
protocol=json.loads((work/'experiments/joint2026_final_protocol.json').read_text())
def sha(p):
 h=hashlib.sha256()
 with Path(p).open('rb') as f:
  for b in iter(lambda:f.read(1048576),b''):h.update(b)
 return h.hexdigest()
def percentile(a,q):
 a=sorted(a);x=(len(a)-1)*q;lo=int(x);hi=min(lo+1,len(a)-1)
 return a[lo]+(x-lo)*(a[hi]-a[lo])
def runtime(repo):
 return {str(p.relative_to(repo)):sha(p) for p in [repo/'build/scratch/network-load-balance',*sorted((repo/'build').glob('*.so'))]}
def verify_runtime(repo,label,expected):
 if runtime(repo)==expected:return 'live'
 assert label=='baselines','GUARD runtime changed after freeze'
 directory=repo/'experiments/results/generalize_frozen_runtime'
 archived=json.loads((directory/'manifest.json').read_text())
 archive=directory/'original-6c438d7-runtime.tar.gz'
 assert archived['runtime']==expected and sha(archive)==archived['archive_sha256']
 found={}
 with tarfile.open(archive,'r:gz') as tf:
  for member in tf:
   assert member.isfile() and member.name in expected
   h=hashlib.sha256();f=tf.extractfile(member)
   for b in iter(lambda:f.read(1048576),b''):h.update(b)
   found[member.name]=h.hexdigest()
 assert found==expected
 return 'archived original runtime, every member verified'
plans={};runs=[];records=[];manifest=[];audited=0;runtime_checks={};telemetry_integrity=[]
roots=[(work,'joint_final_guard','guard'),(original,'joint_final_baselines','baselines')]
for repo,name,label in roots:
 root=repo/'experiments/results'/name;plan=json.loads((root/'plan.json').read_text())
 while True:
  rs=json.loads((root/'results.json').read_text()) if (root/'results.json').exists() else []
  if len(rs)==len(plan['inputs'])*len(plan['variants']):break
  assert '--wait' in sys.argv,'Campaign is incomplete'
  pid=(root/'pid.txt').read_text().strip();proc=Path('/proc')/pid/'cmdline'
  assert proc.exists() and name.encode() in proc.read_bytes(),'Campaign stopped before completion'
  print('AUDIT_WAIT',name,len(rs),'/',len(plan['inputs'])*len(plan['variants']),flush=True);time.sleep(50)
 plans[label]=plan
 assert plan['seeds']==list(range(91001,91011))==protocol['validation_inputs']
 assert plan['reserved_holdout_seeds']==protocol['validation_inputs']
 assert plan['source_diff_sha256']==hashlib.sha256(b'').hexdigest()
 assert plan['runtime']==protocol[label+'_runtime']
 runtime_checks[label]=verify_runtime(repo,label,plan['runtime'])
 assert plan['variants']==(protocol['variants'] if label=='guard' else protocol['baseline_variants'])
 for c in ['WebSearch','AliStorage2019']:assert sha(repo/'traffic_gen'/f'{c}.txt')==plan['cdf_hashes'][c]==protocol['cdf_hashes'][c]
 expected={(x['case'],x['seed'],a) for x in plan['inputs'] for a in plan['variants']}
 assert len(rs)==len(expected) and {(r['case'],r['seed'],r['arm']) for r in rs}==expected
 assert all(r['status']=='completed' and r['exit_code']==0 for r in rs)
 for r in rs:
  assert r['git']==plan['git'];out=Path(r['output_dir'])
  for name,digest in r['output_hashes'].items():assert sha(out/name)==digest,(r['key'],name);audited+=1
  trace=json.loads((root/'inputs'/f'{r["case"]}-{r["seed"]}.json').read_text())
  assert sha(trace['flow_file'])==r['input_sha256']==trace['flow_sha256']
  fresh=json.loads(json.dumps(summarize(out,trace)))
  for k in ['metrics','operations','stats','pfc','completed','analyzed','integrity']:assert fresh[k]==r[k],(r['key'],k)
  raw=[list(map(int,l.split())) for l in (out/(out.name+'_out_fct.txt')).read_text().splitlines() if l.strip()]
  assert all(len(x)==8 for x in raw) and len(raw)==trace['flow_count']==r['completed']
  warm=2e9+trace['duration']*plan['warmup_fraction']*1e9
  fcts=[x[6]/1000 for x in raw if x[5]>=warm];assert len(fcts)==r['tails']['all']['n']
  for q in [95,99]:
   value=percentile(fcts,q/100);assert math.isclose(value,r['tails']['all'][f'p{q}_fct_us'],rel_tol=1e-12,abs_tol=1e-8)
   records.append({'case':r['case'],'seed':r['seed'],'arm':r['arm'],'group':'all','metric':f'p{q}_fct_us','sample_count':len(fcts),'value_us':value})
  manifest.append({'case':r['case'],'seed':r['seed'],'arm':r['arm'],'completed':r['completed'],'analyzed':len(fcts),'output_dir':str(out),'input_sha256':r['input_sha256'],'fct_sha256':r['output_hashes'][out.name+'_out_fct.txt']})
  if r['arm']=='guard':
   from collections import Counter
   counters=Counter();stats_file=out/(out.name+'_out_guard_stats.txt')
   for line in stats_file.read_text().splitlines():
    a=line.split()
    if len(a)==4 and a[0]=='node':
     try:counters[a[2]]+=int(a[3])
     except ValueError:pass
   assert counters['guard_scheduled_acks_without_int']==0,r['key']+' ACK lost telemetry'
   assert counters['guard_compact_scheduled_packets']>0
   telemetry_integrity.append({'case':r['case'],'seed':r['seed'],'scheduled_acks_without_int':counters['guard_scheduled_acks_without_int'],'compact_scheduled_packets':counters['guard_compact_scheduled_packets'],'compact_short_packets':counters['guard_compact_short_packets']})
  print('AUDITED',r['key'],flush=True)
 runs.extend(rs)
assert len(runs)==360
assert plans['guard']['inputs']==plans['baselines']['inputs']
assert plans['guard']['common']==plans['baselines']['common'] and plans['guard']['warmup_fraction']==plans['baselines']['warmup_fraction']==.25
for g in [r for r in runs if r['arm']=='guard']:
 for b in [r for r in runs if r['case']==g['case'] and r['seed']==g['seed'] and r['arm']!='guard']:
  assert g['input_sha256']==b['input_sha256']
  clean=lambda p:{k:v for k,v in p.items() if not k.startswith('guard_') and k not in {'cc','flow_file'}}
  assert clean(g['params'])==clean(b['params'])
def interval(xs):
 assert len(xs)==10;n=len(xs);mean=statistics.fmean(xs);margin=2.2621571627409915*statistics.stdev(xs)/math.sqrt(n)
 return {'n_seeds':n,'mean':mean,'ci95_low':mean-margin,'ci95_high':mean+margin}
arms=['guard','hpcc','dcqcn','homa'];summary=[];effects=[]
for case,group,metric in sorted({(r['case'],r['group'],r['metric']) for r in records}):
 by={(r['seed'],r['arm']):r for r in records if (r['case'],r['group'],r['metric'])==(case,group,metric)}
 for arm in arms:
  rows=[by[s,arm] for s in protocol['validation_inputs']]
  summary.append({'case':case,'group':group,'metric':metric,'arm':arm,'n_min':min(r['sample_count'] for r in rows),'n_max':max(r['sample_count'] for r in rows),**interval([r['value_us'] for r in rows])})
 for baseline in arms[1:]:
  reductions=[100*(1-by[s,'guard']['value_us']/by[s,baseline]['value_us']) for s in protocol['validation_inputs']]
  effects.append({'case':case,'group':group,'metric':metric,'baseline':baseline,'seeds':protocol['validation_inputs'],'reductions_percent':reductions,**interval(reductions)})
health=[];keys=['switch_drops_total','timeout_recoveries','irn_retransmit_packets','homa_retransmit_packets','recovery_nacks_generated','proactive_releases','registrations','reactive_binding_rate_changes','grant_event_rate_changes']
for case in sorted({r['case'] for r in runs}):
 for arm in arms:
  rows=[r for r in runs if (r['case'],r['arm'])==(case,arm)]
  health.append({'case':case,'arm':arm,'runs':len(rows),'completed':sum(r['completed'] for r in rows),**{k:sum(r['stats'][k] for r in rows) for k in keys},'pfc_pause_events':sum(r['pfc']['pfc_pause_events'] for r in rows)})
primary=[e for e in effects if e['baseline']=='homa' and e['metric'] in ('p95_fct_us','p99_fct_us')]
sensitivity=[]
for case in sorted({r['case'] for r in records}):
 for metric in ['p95_fct_us','p99_fct_us']:
  by={(r['seed'],r['arm']):r['value_us'] for r in records if r['case']==case and r['metric']==metric}
  reductions=[100*(1-by[seed,'guard']/min(by[seed,arm] for arm in ['homa','homa_repeat2','homa_repeat3'])) for seed in protocol['validation_inputs']]
  sensitivity.append({'case':case,'metric':metric,'baseline':'fastest of three prespecified Homa executions per input','reductions_percent':reductions,**interval(reductions)})

# Recheck both frozen runtimes after any wait for the other campaign.
for repo,_,label in roots:runtime_checks[label]=verify_runtime(repo,label,protocol[label+'_runtime'])
result={'protocol':protocol,'plans':plans,'runtime_checks':runtime_checks,'runs':len(runs),'completed_records':sum(r['completed'] for r in runs),'summary':summary,'effects':effects,'health':health,'audited_files':audited,'homa_sensitivity':sensitivity,'robust_target_met':len(sensitivity)==12 and all(e['mean']>10 for e in sensitivity),'telemetry_integrity':telemetry_integrity,'primary_metrics':['p95_fct_us','p99_fct_us'],'primary_target_met':len(primary)==12 and all(e['mean']>10 for e in primary),'policy':'All prespecified workloads, algorithms and repetitions retained. Complete input identities and counts verified; no completion-window censoring. Independent P95/P99 calculation after fixed start-time warmup; mean of paired reductions, not pooled flows.'}
out=work/'experiments/results/joint_final_audit';out.mkdir(exist_ok=True)
(out/'report-analysis.json').write_text(json.dumps(result,indent=2)+'\n')
for name,rows in [('per-run',records),('summary',summary),('effects',effects),('health',health),('run-manifest',manifest)]:
 with (out/(name+'.csv')).open('w',newline='') as f:
  writer=csv.DictWriter(f,fieldnames=list(rows[0]));writer.writeheader();writer.writerows(rows)
for e in effects:
 if e['baseline']=='homa':print(e['case'],e['metric'],*[round(e[k],3) for k in ['mean','ci95_low','ci95_high']])
print('AUDIT PASSED',result['runs'],result['completed_records'],audited,'TARGET MET',result['primary_target_met'])

print('FASTEST-OF-THREE HOMA SENSITIVITY',result['robust_target_met'])
for e in sensitivity: print(e['case'],e['metric'],'conservative reduction',round(e['mean'],3))
