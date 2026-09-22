"""Validate sampled feedback diagnostics and report all full DP2 flows."""
import csv,json,re
from pathlib import Path
from collections import defaultdict
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
ROOT=Path(__file__).resolve().parents[1]

def main():
 summaries=[]
 fig,axs=plt.subplots(1,2,figsize=(11,4))
 for arm,color in [('dp2_joint32_trace','#0072B2')]:
  rec=json.loads((ROOT/'runs'/('allreduce_dp2-s301-'+arm)/'result.json').read_text());assert rec['status']=='completed'
  d=Path(rec['output_dir']);trace=next(d.glob('*controller.csv'));lines=trace.read_text().splitlines()
  footer=[l for l in lines if l.startswith('#')]
  attempted,written,truncated=map(int,re.findall(r'\d+',footer[0]));sampled=int(re.search(r'sampled_out=(\d+)',footer[1]).group(1))
  assert truncated==0 and attempted==written+sampled
  data=list(csv.DictReader(l for l in lines if not l.startswith('#')));assert len(data)==written
  byflow=defaultdict(list)
  for v in data:byflow[int(v['flow_id'])].append(v)
  assert set(byflow)==set(range(1280))
  inp=np.loadtxt(rec['flow'],skiprows=1,ndmin=2);fct=np.loadtxt(next(d.glob('*_out_fct.txt')),dtype=np.int64,ndmin=2)
  bound=rec['extra'].get('guard_recovery_max_rtts',0);stats=[]
  for fid,vs in byflow.items():
   c=[v for v in vs if v['event_type']=='complete'];assert len(c)==1
   idx=vs.index(c[0]);assert all(v['time_ns']==c[0]['time_ns'] for v in vs[idx+1:]);vs=vs[:idx+1]
   start=round(inp[fid,4]*1e9);m=fct[(fct[:,0]==inp[fid,0])&(fct[:,1]==inp[fid,1])&(abs(fct[:,5]-start)<=2)];assert len(m)==1
   assert int(c[0]['time_ns'])==int(m[0,5]+m[0,6]);assert int(c[0]['snd_nxt'])==int(c[0]['snd_una'])==int(inp[fid,3])
   gaps=[];rates=[];congestion=[];boosted=0
   for v in vs:
    assert 100000000 <= int(v['final_rate_bps']) <= 100000000000
    assert int(v['last_full_feedback_ns'])<=int(v['time_ns'])
    inc=int(v['last_recovery_ai_bps']);gap=int(v['last_full_gap_ns'])
    if inc==0:continue
    # In these unchanged DP2 inputs, fixed original window=104000B on100Gbps,
    # i.e. original baseRTT8320ns. No post-grant window enlargement used.
    assert int(v['window_bytes'])==104000
    expect=40000000 if bound<=1 or gap<=8320 else min(40000000*gap//8320,40000000*bound)
    assert inc==expect,(arm,fid,gap,inc,expect)
    gaps.append(gap/1000);rates.append(int(v['final_rate_bps'])/1e9);congestion.append(float(v['stored_congestion_metric']));boosted+=inc>40000000
   stats.append(dict(flow_id=fid,fct_ms=m[0,6]/1e6,samples=len(gaps),
    median_last_full_gap_us=float(np.median(gaps)) if gaps else None,
    sampled_fraction_low_rate=float(np.mean(np.array(rates)<1)) if rates else None,
    median_stored_congestion=float(np.median(congestion)) if congestion else None,
    sampled_fraction_boosted=boosted/len(gaps) if gaps else None))
  stats.sort(key=lambda v:v['fct_ms'],reverse=True);slow=stats[:13];rest=stats[13:]
  for subset,style,name in [(slow,'--','slowest13'),(rest,'-','other1267')]:
   x=np.sort([r['median_last_full_gap_us'] for r in subset if r['median_last_full_gap_us'] is not None])
   axs[0].plot(x,np.arange(1,len(x)+1)/len(x),ls=style,color=color,label=arm.replace('dp2_','').replace('_trace','')+' '+name)
  axs[1].scatter([v['median_last_full_gap_us'] for v in stats],[v['fct_ms'] for v in stats],s=7,alpha=.35,color=color,label=arm.replace('dp2_','').replace('_trace',''),rasterized=True)
  summaries.append(dict(arm=arm,rows=written,complete_events=1280,cap_truncations=0,formula_checks='all nonzero sampled stored increments match actual8320ns baseRTT and bound',
   slow13_mean_sample_fraction_low_rate=float(np.mean([v['sampled_fraction_low_rate'] for v in slow])),
   slow13_median_of_flow_median_gaps_us=float(np.median([v['median_last_full_gap_us'] for v in slow])),flows=stats))
 axs[0].set(xlabel='Per-flow median sampled feedback gap (µs)',ylabel='CDF');axs[0].set_xscale('log');axs[0].legend(fontsize=7)
 axs[1].set(xlabel='Per-flow median sampled feedback gap (µs)',ylabel='Full flow FCT (ms)');axs[1].set_xscale('log');axs[1].legend(fontsize=8)
 fig.suptitle('Full DP2; observed seed301; event-sampled state, not exact time residency');fig.tight_layout();(ROOT/'figures').mkdir(exist_ok=True)
 fig.savefig(ROOT/'figures/feedback_gaps.png',dpi=170);fig.savefig(ROOT/'figures/feedback_gaps.pdf');plt.close(fig)
 (ROOT/'trace_analysis.json').write_text(json.dumps(summaries,indent=2)+'\n')
 for s in summaries:print({k:v for k,v in s.items() if k!='flows'})
if __name__=='__main__':main()
