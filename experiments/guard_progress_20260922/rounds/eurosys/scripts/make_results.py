"""Export auditable, paired seed effects as LaTeX macros and JSON."""
from collections import defaultdict
import json
import re
from pathlib import Path
import numpy as np
ROOT=Path(__file__).resolve().parents[1]
data=json.loads((ROOT/'analysis.json').read_text())
groups=defaultdict(list)
for r in data['runs']:groups[r['study'],r['arm']].append(r)
sn={'ali30':'AliThirty','ali50':'AliFifty','web40':'Web','fb40':'Fb','fabric':'Fabric','receiver':'Receiver','receiver2':'ReceiverTwo','hybrid':'Hybrid','alltoall':'AtoA','allreduce_dp2':'Dp','ring':'Ring','fairness':'Fairness'}
an={'guard':'Guard','hpcc':'Hpcc','homa':'Homa','dcqcn':'Dcqcn','timely':'Timely','no_oflm':'NoOflm','no_selective':'NoSelective','no_release':'NoRelease','keep_last_hop':'KeepLast','receiver_only':'ReceiverOnly','lambda1':'LambdaOne','lambda14':'LambdaFourteen'}
mn={'fct_mean_us':'Mean','slowdown_p99':'Tail','span_ms':'Span','queue_fixed_mean_kb':'Queue','grants':'Grants','mean_flow_goodput_gbps':'FlowRate','drops':'Drops','timeout_recoveries':'Timeouts','fabric_bindings':'FabricBindings','receiver_bindings':'ReceiverBindings'}
lines=['% Generated exclusively from validated new runs.']; claims={}; effects={}
def export(name,value):lines.append('\\newcommand{\\'+name+'}{'+value+'}')
def ci(v):
 v=np.array(v,float);return float(v.mean()),float(2.776445105*v.std(ddof=1)/np.sqrt(len(v))) if len(v)>1 else 0
for s,sname in sn.items():
 for a,aname in an.items():
  rs=groups[s,a]
  for m,mname in mn.items():
   name=sname+aname+mname;vs=[r['metrics'][m] for r in rs]
   if len(vs)==5:
    mean,e=ci(vs);export(name,f'{mean:.2f}');claims[name]={'values':vs,'mean':mean,'ci95':[mean-e,mean+e],'runs':[r['key'] for r in rs]}
   else:export(name,r'\textit{pending}')
  if a=='guard':continue
  g={r['seed']:r for r in groups[s,'guard']}
  for m,mname in mn.items():
   name=sname+'Vs'+aname+mname
   pairs=[(g[r['seed']],r) for r in rs if r['seed'] in g and r['metrics'][m]!=0]
   if len(pairs)==5:
    vs=[100*(x['metrics'][m]/y['metrics'][m]-1) for x,y in pairs];mean,e=ci(vs)
    export(name,f'{mean:+.2f}\\%');export(name+'CI',f'[{mean-e:+.2f}, {mean+e:+.2f}]\\%')
    effects[name]={'values':vs,'mean':mean,'ci95':[mean-e,mean+e],'pairs':[[x['key'],y['key']] for x,y in pairs]}
   else:
    export(name,r'\textit{pending}');export(name+'CI',r'\textit{pending}')
for a in ['Hpcc','Dcqcn','Timely']:
 names=[sn[s]+'Vs'+a+'Mean' for s in ['ali30','ali50','web40','fb40']]
 if all(n in effects for n in names):
  reductions=[-effects[n]['mean'] for n in names]
  export('MeanReductionRange'+a,f'{min(reductions):.1f}--{max(reductions):.1f}\\%')
 else:export('MeanReductionRange'+a,r'\textit{pending}')
used=set(re.findall(r'\\([A-Za-z]+)', '\n'.join(p.read_text() for p in (ROOT/'paper/sections').glob('*.tex'))))
lines=[line for line in lines if line.startswith('%') or re.search(r'\\newcommand\{\\([A-Za-z]+)',line).group(1) in used]
(ROOT/'paper/results.tex').write_text('\n'.join(lines)+'\n')
(ROOT/'claim_evidence.json').write_text(json.dumps({'absolute':claims,'paired_effects':effects},indent=2)+'\n')
print('Exported',len(claims),'absolute and',len(effects),'paired five-seed quantities')
