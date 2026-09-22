"""Validate complete Analytics traces and the identified startup-estimate bug."""
import csv,json,re
from pathlib import Path
from collections import Counter
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
ROOT=Path(__file__).resolve().parents[1]
ARMS=['diagnose_shared_fb_trace','diagnose_peer_trace','fixed_trace_peer_trace','fixed_trace_joint8_fb_trace']
LABELS=['Startup off','Before fix','After fix','After fix + recovery8']
def main():
 rows=[];fig,axs=plt.subplots(1,2,figsize=(10,4))
 for arm,label,style in zip(ARMS,LABELS,['-', '-', '--', ':']):
  r=json.loads((ROOT/'runs'/('fb40-s301-'+arm)/'result.json').read_text());d=Path(r['output_dir']);trace=next(d.glob('*controller.csv'))
  lines=trace.read_text().splitlines();footer=[v for v in lines if v.startswith('#')]
  attempted,written,_=map(int,re.findall(r'\d+',footer[0]));sampled=int(re.search(r'sampled_out=(\d+)',footer[1]).group(1))
  assert attempted-written-sampled==0
  data=list(csv.DictReader(v for v in lines if not v.startswith('#')));assert len(data)==written
  done={int(v['flow_id']):v for v in data if v['event_type']=='complete'};assert len(done)==r['flow_count']==6615
  assert sum(v['event_type']=='complete' for v in data)==len(done)
  assert set(done)==set(range(6615))
  inp=np.loadtxt(r['flow'],skiprows=1);fct=np.loadtxt(next(d.glob('*_out_fct.txt')),dtype=np.int64)
  for fid,c in done.items():
   v=inp[fid];m=fct[(fct[:,0]==v[0])&(fct[:,1]==v[1])&(fct[:,4]==v[3])&(abs(fct[:,5]-round(v[4]*1e9))<=2)]
   assert len(m)==1 and int(c['time_ns'])==int(m[0,5]+m[0,6])
  summary=dict(arm=arm,rows=len(data),completed=len(done),cap_omissions=0,flows={})
  for fid in [4089,4260,4572]:
   vs=[v for v in data if int(v['flow_id'])==fid];start=round(inp[fid,4]*1e9)
   summary['flows'][str(fid)]=dict(fct_us=(int(done[fid]['time_ns'])-start)/1000,
    fabric_caps_bps=sorted({int(v['hpcc_rate_bps']) for v in vs}),events=dict(Counter(v['event_type'] for v in vs)))
  releases=[v for v in data if v['event_type']=='startup_path_release'];summary['release_events']=releases
  if arm.startswith('fixed'):
   assert len(releases)==1 and releases[0]['flow_id']=='4572'
   v=releases[0];assert v['nhop']=='0' and int(v['hpcc_rate_bps'])==100000000000
   assert int(v['final_rate_bps'])==min(int(v['hpcc_rate_bps']),int(v['grant_rate_bps']))
   assert summary['flows']['4572']['fabric_caps_bps']==[100000000000]
  elif arm=='diagnose_peer_trace':assert summary['flows']['4572']['fabric_caps_bps']==[50000000000]
  vs=[v for v in data if v['flow_id']=='4572'];start=round(inp[4572,4]*1e9)
  x=np.array([int(v['time_ns'])-start for v in vs])/1e6
  axs[0].plot(x,[int(v['snd_nxt'])/1e6 for v in vs],label=label,ls=style)
  axs[1].step(x,[int(v['hpcc_rate_bps'])/1e9 for v in vs],where='post',label=label,ls=style)
  rows.append(summary)
 axs[0].set(ylabel='Sent payload (MB)',xlabel='Time since flow start (ms)');axs[0].legend(fontsize=8)
 axs[1].set(ylabel='Sampled fabric cap (Gbps)',xlabel='Time since flow start (ms)',ylim=(0,110))
 fig.suptitle('Analytics flow4572 (11→14); development seed301; full-trace diagnosis');fig.tight_layout();(ROOT/'figures').mkdir(exist_ok=True)
 fig.savefig(ROOT/'figures/startup_diagnosis.png',dpi=170);fig.savefig(ROOT/'figures/startup_diagnosis.pdf');plt.close(fig)
 (ROOT/'startup_diagnosis.json').write_text(json.dumps(rows,indent=2)+'\n')
 print('PASS: four complete6615-flow traces; diagnosed50Gbps stale startup cap; actual no-fabric release event and receiver cap verified')
 for r in rows:print(r['arm'],r['flows']['4572']['fct_us'],r['flows']['4260']['fct_us'])
if __name__=='__main__':main()
