"""Validate actual receiver sampler windows and every promotion/demotion."""
import csv,json
from pathlib import Path
from collections import defaultdict,Counter
ROOT=Path(__file__).resolve().parents[1]
def stats(row):
 path=next(Path(row['output_dir']).glob('*guard_stats.txt'));out={}
 for line in path.read_text().splitlines():
  if not line.startswith('guard_utilization_width '):continue
  v=line.split()[1:];d={k:int(n) for k,n in zip(v[::2],v[1::2])};out[d['node']]=d
 return out

def main():
 a=json.loads((ROOT/'analysis.json').read_text());idx={(r['study'],r['arm']):r for r in a['runs']};result={}
 for st in ['ali30','ali50','hybrid']:
  on=idx[st,('hybrid_trace' if st=='hybrid' else 'width_trace')+'_adaptive_activity_trace'];off=idx[st,'width_adaptive_width'];ss=stats(on)
  assert ss==stats(off)
  rows=[]
  for v in csv.DictReader(l for l in next(Path(on['output_dir']).glob('*grants.csv')).open() if not l.startswith('#')):
   for k in v:
    if k not in ['event','set_change']:v[k]=int(v[k])
   rows.append(v)
  snapshots=defaultdict(set);samples={};changes=defaultdict(list)
  for v in rows:
   if v['event'] not in ['sent','utilization_sample']:continue
   key=v['host_node'],v['time_ns'];value=v['host_data_payload_bytes']
   snapshots[key].add(value)
   if v['event']=='utilization_sample':assert key not in samples;samples[key]=v
   elif v['set_change']=='utilization_width':changes[key].append(v)
  nodes=defaultdict(Counter);promotions=[];demotions=[];checked=0;ambiguous_times=sum(len(v)>1 for v in snapshots.values());consecutive=0;epoch_starts=0
  for key,v in sorted(samples.items()):
   node,time=key;elapsed=v['utilization_interval_ns'];assert elapsed in [4160,8320],elapsed
   assert (node,time-elapsed) in snapshots,(st,key,elapsed)
   previous=samples.get((node,time-elapsed))
   candidates={previous['host_data_payload_bytes']} if previous else snapshots[node,time-elapsed]
   compatible=[x for x in candidates if (v['host_data_payload_bytes']-x)*8000000000//elapsed==v['utilization_payload_bps']]
   assert len(compatible)==1,(st,key,candidates,v['utilization_payload_bps'])
   consecutive+=int(previous is not None);epoch_starts+=int(previous is None)
   data=v['host_data_payload_bytes']-compatible[0];rate=data*8000000000//elapsed
   assert rate==v['utilization_payload_bps'];checked+=1;nodes[node]['checks']+=1
   assert v['distinct_senders']>=2 and v['active_flows']>=2
   low=v['utilization_low_windows'];high=v['utilization_high_windows'];wide=v['utilization_wide'];line=v['line_rate_bps']
   assert 0<=low<=2 and 0<=high<=2 and wide in [0,1]
   assert (low>0)==(rate<line*7//10) and (high>0)==(rate>=line*85//100)
   if low==2 or high==2:
    previous=samples.get((node,time-elapsed));assert previous is not None
    field='utilization_low_windows' if low==2 else 'utilization_high_windows'
    assert previous[field]>=1
   promote=not wide and low==2;demote=wide and high==2
   assert bool(changes.get(key))==bool(promote or demote),(st,key,wide,low,high)
   if promote or demote:
    emitted=changes[key];assert len(emitted)==v['active_flows']
    assert len({x['flow_id'] for x in emitted})==len(emitted)
    assert all(x['utilization_wide']==int(promote) for x in emitted)
    record=dict(node=node,time_ns=time,rate_bps=rate,interval_ns=elapsed,active_flows=v['active_flows'],grants=len(emitted))
    if promote:promotions.append(record);nodes[node]['promotions']+=1
    else:demotions.append(record);nodes[node]['demotions']+=1
  assert set(changes)<=set(samples)
  for node,s in ss.items():
   assert s['enabled']==1
   for key in ['checks','promotions','demotions']:assert s[key]==nodes[node][key],(st,node,key,s[key],nodes[node][key])
  result[st]=dict(sample_windows=checked,same_timestamp_multiple_counters=ambiguous_times,consecutive_sample_baselines=consecutive,epoch_start_baselines=epoch_starts,baseline_note="Consecutive windows use the preceding actual sample. First windows require exactly one rate-compatible counter among observations at the epoch start; same-time event order is not inferred.",promotions=promotions,demotions=demotions,all_transitions_verified=True,trace_neutral_counts=True)
  print(st,'verified',checked,'actual RTT windows;',len(promotions),'promotions;',len(demotions),'demotions',flush=True)
 (ROOT/'width_trace_validation.json').write_text(json.dumps(result,indent=2)+'\n')
if __name__=='__main__':main()
