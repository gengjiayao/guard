import json,csv,re
from pathlib import Path
from collections import defaultdict,Counter,deque
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from report import ROOT,save,rows

def main():
 a=json.loads((ROOT/'analysis.json').read_text());idx={(r['study'],r['arm']):r for r in a['runs']};out={};grants={};controllers={};fcts={}
 for profile,label,base in [('activity_trace','K1','shared_rescue'),('adaptive_activity_trace','Conditional','adaptive_width')]:
  r=idx['hybrid','hybrid_trace_'+profile];b=idx['hybrid','width_'+base];assert r['fct_sha256']==b['fct_sha256'] and r['metrics']==b['metrics']
  rec=json.loads((ROOT/'runs'/r['key']/'result.json').read_text());flow=np.loadtxt(rec['flow'],skiprows=1);fct=np.loadtxt(r['fct_file'],dtype=np.int64);assert len(flow)==len(fct)==5
  p=next(Path(r['output_dir']).glob('*grants.csv'));g=rows(p);c=rows(next(Path(r['output_dir']).glob('*controller.csv')));rx=rows(Path(str(p)+'.rx.csv'))
  expected=Counter();packets=Counter()
  for f in flow:expected[int(f[1])]+=int(f[3]);packets[int(f[1])]+=(int(f[3])+999)//1000
  for v in rx:
   n=int(v['node_id']);assert int(v['payload_bytes'])==expected[n] and int(v['packets'])==packets[n] and int(v['nics'])==1
  assert set(expected)<={int(v['node_id']) for v in rx}
  for file in [p,next(Path(r['output_dir']).glob('*controller.csv'))]:
   footer=next(x for x in file.read_text().splitlines() if x.startswith('#'));assert re.search(r'(truncated|cap_omissions)[= ]0',footer),footer
  counts=Counter(int(v['flow_id']) for v in c if v['event_type']=='complete');assert counts==Counter(range(5))
  q=defaultdict(deque);received=0
  for v in g:
   for k in v:
    if k not in ['event','set_change']:v[k]=int(v[k])
   key=v['flow_id'],v['generation'],v['grant_rate_bps']
   if v['event']=='sent':q[key].append(v)
   if v['event']=='received':assert q[key].popleft()['time_ns']<=v['time_ns'];received+=1
  assert not any(q.values())
  values=[]
  for i,f in enumerate(flow):
   matches=[v for v in fct if int(v[0])==int(f[0]) and int(v[1])==int(f[1]) and int(v[4])==int(f[3]) and abs(int(v[5])-round(f[4]*1e9))<=2];assert len(matches)==1
   values.append(float(matches[0][6])/1e6)
  fcts[label]=values;grants[label]=g;controllers[label]=c
  out[label]=dict(trace_neutral=True,data_conservation=True,selected_flows=5,completed_flows=5,grant_pairs=received,cap_omissions=0,perflow_fct_ms=values,metrics=r['metrics'])
 samples=[v for v in grants['Conditional'] if v['event']=='utilization_sample'];changes=[v for v in grants['Conditional'] if v['set_change']=='utilization_width' and v['event']=='sent'];times=sorted({v['time_ns'] for v in changes});assert len(times)==2
 out['transitions']=changes;out['inference']='Low receiver arrival does not distinguish sender/fabric limitation from scheduling stalls. A low cap on the active primary and simultaneous promotion support a fabric-contention hypothesis; these traces do not prove a particular fix.'
 (ROOT/'hybrid_diagnosis.json').write_text(json.dumps(out,indent=2)+'\n')
 fig,axs=plt.subplots(3,1,figsize=(11,10),sharex=True)
 axs[0].plot([(v['time_ns']-2e9)/1e6 for v in samples],[v['utilization_payload_bps']/1e9 for v in samples],lw=1,label='Actual RTT window')
 for x in [70,85]:axs[0].axhline(x,ls='--',color='gray',alpha=.6)
 axs[0].set(ylabel='Receiver DATA (Gb/s)',ylim=(0,110));axs[0].legend()
 for fid,color in [(1,'#ce6a27'),(4,'#167c67')]:
  g=[v for v in grants['Conditional'] if v['event']=='sent' and v['flow_id']==fid];axs[1].step([(v['time_ns']-2e9)/1e6 for v in g],[v['grant_rate_bps']/1e9 for v in g],where='post',label=f'Flow {fid}',color=color)
  c=[v for v in controllers['Conditional'] if int(v['flow_id'])==fid];axs[2].plot([(int(v['time_ns'])-2e9)/1e6 for v in c],[int(v['hpcc_rate_bps'])/1e9 for v in c],label=f'Flow {fid}',color=color,lw=1)
 for ax in axs:
  ax.grid(alpha=.2);ax.legend(loc='upper right')
  for t in times:ax.axvline((t-2e9)/1e6,color='black',ls=':',alpha=.5)
 axs[1].set(ylabel='Receiver grant (Gb/s)',ylim=(0,110));axs[2].set(ylabel='Sender fabric cap (Gb/s)',xlabel='Time since 2 s (ms)',ylim=(0,110),xlim=(1.65,3.4))
 fig.suptitle('Hybrid: conditional widening and fabric-rate oscillation; seed 301');save(fig,'hybrid_timeline')
 fig,ax=plt.subplots(figsize=(9,4));x=np.arange(5)
 for off,label in [(-.18,'K1'),(.18,'Conditional')]:ax.bar(x+off,fcts[label],width=.36,label=label)
 ax.set(xticks=x,xticklabels=[f'{i}: {int(f[0])} → {int(f[1])}' for i,f in enumerate(flow)],xlabel='Flow ID: source → destination',ylabel='FCT (ms)',title='Hybrid: all five original 8 MiB flows, seed 301');ax.grid(axis='y',alpha=.2);ax.legend();save(fig,'hybrid_flows')
 with (ROOT/'REPORT.zh.md').open('a') as f:f.write('\n## Hybrid 回退定位\n\n两组增加观测的重跑均与各自无观测运行的逐流 FCT 和全部指标精确一致，五条原始 8 MiB 流全部完成，DATA 守恒、授权发送/接收匹配且日志无截断。\n\n接收端 5 在相对 2 s 的 1.8116 ms 增加并发：流 1/4 各获约 50 Gb/s；3.19272 ms 退出。流 4 的发送路径限速随后低于原高授权，额外启用流 1 又增加了同一网络的竞争。这支持“低到达速率可能来自路径限速”的解释，不能仅凭利用率判断有可用容量。下一步应使用真实传输且有新鲜度校验的发送端反馈区分原因，并计入控制报文开销。\n\n![](figures/hybrid_timeline.png)\n\n![](figures/hybrid_flows.png)\n')
 print('Hybrid: both trace pairs exact, conservation and all selected flows verified')
if __name__=='__main__':main()
