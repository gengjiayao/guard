#!/usr/bin/env python3
"""Compare complete development repetitions with immutable original Homa."""
from pathlib import Path
import json,sys,statistics,hashlib,math
REPO=Path(__file__).resolve().parents[1]
fixed=Path('/home/gengjiayao/ict/guard/experiments/results')
refs={}
for campaign in ['generalize_frozen_baseline','generalize_frozen_baseline3','generalize_final_baselines']:
 for r in json.loads((fixed/campaign/'results.json').read_text()):
  if r['arm']=='homa' and r['status']=='completed':
   key=(r['case'],r['seed']);assert key not in refs
   refs[key]=r

def pct(values,q):
 a=sorted(values);x=(len(a)-1)*q;i=int(x)
 return a[i]+(x-i)*(a[min(i+1,len(a)-1)]-a[i])
for arg in sys.argv[1:]:
 root=REPO/'experiments/results'/arg
 if not (root/'results.json').exists():print(arg,'0 complete');continue
 plan=json.loads((root/'plan.json').read_text());rs=json.loads((root/'results.json').read_text());groups={};rows=[]
 for r in rs:
  if r['status']!='completed':print('FAILED',r['key'],r.get('error'));continue
  b=refs[(r['case'],r['seed'])];assert r['input_sha256']==b['input_sha256']
  ignored={'cc','flow_file'}
  params=lambda v:{k:x for k,x in v['params'].items() if k not in ignored and not k.startswith('guard_')}
  assert params(r)==params(b),(r['key'],'different non-GUARD conditions')
  p=Path(r['output_dir']);raw=p/(p.name+'_out_fct.txt')
  assert hashlib.sha256(raw.read_bytes()).hexdigest()==r['output_hashes'][raw.name]
  lines=[list(map(int,l.split())) for l in raw.read_text().splitlines() if l.strip()]
  duration=next(t['duration'] for t in plan['inputs'] if t['case']==r['case'] and t['seed']==r['seed'])
  f=[v[6]/1000 for v in lines if v[5]>=2e9+duration*plan['warmup_fraction']*1e9]
  assert len(lines)==r['completed'] and len(f)==r['tails']['all']['n']
  row={'arm':r['arm'],'case':r['case'],'seed':r['seed'],'completed':r['completed'],'input_sha256':r['input_sha256']}
  for q in [95,99]:
   val=pct(f,q/100);assert math.isclose(val,r['tails']['all'][f'p{q}_fct_us'],rel_tol=1e-12)
   row[f'p{q}_us']=val;row[f'homa_p{q}_us']=b['tails']['all'][f'p{q}_fct_us']
   row[f'p{q}_reduction']=100*(1-val/row[f'homa_p{q}_us'])
  rows.append(row);groups.setdefault((r['arm'],r['case']),[]).append(row)
 summary=[]
 for (arm,case),g in sorted(groups.items()):
  avg={f'p{q}_reduction':statistics.fmean(v[f'p{q}_reduction'] for v in g) for q in [95,99]}
  summary.append(dict(arm=arm,case=case,n=len(g),**avg))
  print(arg,arm,case,'n='+str(len(g)), 'P95=%+.2f%% P99=%+.2f%%'%(avg['p95_reduction'],avg['p99_reduction']))
 (root/'joint-comparison.json').write_text(json.dumps({'rows':rows,'summary':summary,'complete':len(rs)==len(plan['inputs'])*len(plan['variants']),'baseline':'Original 6c438d7 frozen Homa; all completed cases retained'},indent=2)+'\n')
