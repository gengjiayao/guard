"""Full selected-flow grant histories; observations, not performance claims."""
import csv,json,re,hashlib,sys
from pathlib import Path
from collections import Counter,defaultdict,deque
import numpy as np
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'scripts/upstream'))
import campaign

def main():
 a=json.loads((ROOT/'analysis.json').read_text());idx={(r['study'],r['arm']):r for r in a['runs']}
 old=json.loads((ROOT.parent/'guard_grantdiag_20260921/analysis.json').read_text())
 oldidx={(r['study'],r['arm']):r for r in old['runs']};result={}
 for study in ['ali30','ali50']:
  off=idx[study,'width_adaptive_width'];on=idx[study,'width_trace_adaptive_activity_trace'];parent=oldidx[study,'fixed_shared_rescue']
  assert off['fct_sha256']==on['fct_sha256']
  assert off['metrics']==on['metrics']
  rec=json.loads((ROOT/'runs'/on['key']/'result.json').read_text());inp=np.loadtxt(rec['flow'],skiprows=1)
  trace=next(Path(on['output_dir']).glob('*grants.csv'));lines=trace.read_text().splitlines();footer=[l for l in lines if l.startswith('#')]
  attempted,written,truncated=map(int,re.findall(r'\d+',footer[0]));filtered,minimum=map(int,re.findall(r'\d+',footer[1]))
  assert minimum==256001 and filtered>0 and attempted==written and truncated==0
  rows=list(csv.DictReader(l for l in lines if not l.startswith('#')));assert len(rows)==written
  numeric=[k for k in rows[0] if k not in ['event','set_change']]
  expected={i for i,v in enumerate(inp) if v[3]>=minimum};eligible={i for i in expected if inp[i,4]>2+rec['warmup']}
  identity=defaultdict(list)
  for fid in expected:
   v=inp[fid];identity[fid % 65536,int(v[0]),int(v[1]),int(v[3])].append(fid)
  byflow=defaultdict(list);events=Counter();changes=Counter();remapped=0
  for row in rows:
   assert None not in row
   for k in numeric:row[k]=int(row[k])
   fid=row['flow_id']
   assert fid in expected and row['flow_size']==int(inp[fid,3])
   byflow[fid].append(row);events[row['event']]+=1
   if row['event']=='sent':changes[row['set_change']]+=1
  assert set(byflow)==expected
  fct=np.loadtxt(on['fct_file'],dtype=np.int64);ends=defaultdict(list)
  for r in fct:ends[int(r[0]),int(r[1]),int(r[4]),int(r[5])].append(int(r[5]+r[6]))
  perflow=[];unmatched_received=0;unmatched_sent=0;total_latency=0;duration_totals=Counter();send_counts=Counter();delays=[]
  for fid in sorted(expected):
   q=defaultdict(deque);matched=[]
   for row in byflow[fid]:
    key=(row['generation'],row['grant_rate_bps'])
    if row['event']=='sent':q[key].append(row)
    elif row['event']=='received':
     if not q[key]:unmatched_received+=1;continue
     sent=q[key].popleft();assert sent['time_ns']<=row['time_ns'];matched.append((row,sent))
   unmatched_sent+=sum(len(v) for v in q.values())
   if fid not in eligible:continue
   flow=inp[fid];start=round(flow[4]*1e9);possible=[]
   for delta in range(-2,3):possible+=ends[int(flow[0]),int(flow[1]),int(flow[3]),start+delta]
   assert len(possible)==1;(end,)=possible;durations=Counter();counts=Counter()
   total_latency+=end-start
   first=min(end,matched[0][0]['time_ns']) if matched else end
   durations['before_first_grant']+=max(0,first-start)
   def category(s):
    if s['grant_rate_bps']>=s['line_rate_bps']:return 'line_rate'
    prefix='single_sender' if s['distinct_senders']==1 else 'multiple_senders'
    suffix='low_cap' if s['grant_rate_bps']<=100000000 else 'weighted'
    return prefix+'_'+suffix
   for i,(received,sent) in enumerate(matched):
    t=received['time_ns'];until=min(end,matched[i+1][0]['time_ns'] if i+1<len(matched) else end)
    dt=max(0,until-max(t,start));cat=category(sent);durations[cat]+=dt;counts[cat]+=1
    if sent['grant_rate_bps']<sent['line_rate_bps']:
     delays.append(received['time_ns']-sent['time_ns'])
   assert sum(durations.values())==end-start,(fid,durations,end-start)
   duration_totals.update(durations);send_counts.update(counts)
   perflow.append(dict(flow_id=fid,size=int(flow[3]),latency_ns=end-start,durations_ns=dict(durations),grant_counts=dict(counts)))
  result[study]=dict(trace_neutral=True,receiver_id_modulus=None,receiver_records_remapped=remapped,trace_sha256=campaign.sha(trace),selected_all_flows=len(expected),eligible_flows=len(eligible),rows=written,cap_omissions=truncated,size_filtered_events=filtered,event_counts=dict(events),set_changes=dict(changes),unmatched_received=unmatched_received,unmatched_sent=unmatched_sent,
    duration_fractions={k:v/total_latency for k,v in duration_totals.items()},duration_ns=dict(duration_totals),total_eligible_latency_ns=total_latency,grant_counts=dict(send_counts),grant_delivery_delay_us_quantiles={str(k):float(np.percentile(delays,k)/1000) for k in [50,95,99,100]},per_flow=perflow)
  print(study,'selected',len(expected),'rows',written,'events',dict(events),'unmatched',unmatched_sent,unmatched_received,'duration fractions',result[study]['duration_fractions'],flush=True)
 (ROOT/'adaptive_grant_diagnosis.json').write_text(json.dumps(result,indent=2)+'\n')
if __name__=='__main__':main()
