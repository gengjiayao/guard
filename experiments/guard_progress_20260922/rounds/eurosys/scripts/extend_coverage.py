"""Add old two-sender incast and time-series instrumentation; no tuning."""
from copy import deepcopy
import json,random
from campaign import ROOT,ARMS,SEEDS,sha,save,flow_file
p=ROOT/'manifest.json';m=json.loads(p.read_text())
assert not any(t['study']=='receiver2' for t in m['tasks'])
(ROOT/'audit/manifest-initial.json').write_bytes(p.read_bytes())
extra=[]
for seed in SEEDS:
 rng=random.Random(seed);f=ROOT/'flows'/f'receiver2-s{seed}.txt'
 flow_file(f,[(s,8,3,8*1048576,2.001+rng.uniform(0,.5e-6)) for s in [0,4]])
 for arm in ARMS+['receiver_only']:
  t=deepcopy(next(x for x in m['tasks'] if x['study']=='receiver' and x['seed']==seed and x['arm']==arm))
  t.update(study='receiver2',flow=str(f),flow_sha256=sha(f),flow_count=2,monitor='full',extra=dict(qlen_monitoring_interval=1000,sw_monitoring_interval=1000))
  t['key']=f'receiver2-s{seed}-{arm}';extra.append(t)
for study in ['fabric','hybrid']:
 for arm in ARMS+['receiver_only']:
  t=deepcopy(next(x for x in m['tasks'] if x['study']==study and x['seed']==301 and x['arm']==arm))
  t.update(study=study+'_series',monitor='full',extra=dict(qlen_monitoring_interval=1000,sw_monitoring_interval=1000))
  t['key']=f'{study}_series-s301-{arm}';extra.append(t)
m['extensions']=[dict(reason='Coverage audit: reproduce two-sender incast endpoints and retain directed time-series metrics from old manuscript. Same frozen controller settings; no comparison-driven tuning.',tasks_added=len(extra))]
m['tasks']+=extra;save(p,m)
print(len(m['tasks']))
