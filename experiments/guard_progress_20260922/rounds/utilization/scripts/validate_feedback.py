"""Replay receiver-observable report provenance, grant epochs and sampler decisions."""
import csv,json,re
from pathlib import Path
from collections import defaultdict,Counter,deque
from validate_width_trace import stats
ROOT=Path(__file__).resolve().parents[1]
def main():
 a=json.loads((ROOT/'analysis.json').read_text());idx={(r['study'],r['arm']):r for r in a['runs']};out={}
 for st in ['ali50','hybrid']:
  on=idx[st,'feedback_trace_feedback_trace'];off=idx[st,'feedback_feedback_width'];assert on['fct_sha256']==off['fct_sha256'] and on['metrics']==off['metrics'];assert stats(on)==stats(off)
  path=next(Path(on['output_dir']).glob('*grants.csv'));lines=path.read_text().splitlines();footer=next(x for x in lines if x.startswith('#'));assert re.search(r'truncated[= ]0',footer)
  rows=list(csv.DictReader(x for x in lines if not x.startswith('#')))
  for v in rows:
   for k in v:
    if k not in ['event','set_change']:v[k]=int(v[k])
  rtts={};pending=defaultdict(deque);pairs=0;received_grants={}
  for v in rows:
   key=v['flow_id'],v['generation'],v['grant_rate_bps']
   if v['event']=='sent':pending[key].append(v)
   if v['event']=='received':
    assert pending[key].popleft()['time_ns']<=v['time_ns'];pairs+=1;received_grants[v['flow_id'],v['generation']]=v['time_ns']
    assert v['sender_window_bytes'] in [52000,104000]
    rtt=v['sender_window_bytes']*8000000000//v['line_rate_bps'];assert v['flow_id'] not in rtts or rtts[v['flow_id']]==rtt;rtts[v['flow_id']]=rtt
  assert not any(pending.values())
  active={};group=defaultdict(list);group_key={};state={};checks=Counter();nodes=defaultdict(Counter);decisions=[];snapshots=defaultdict(set);samples={};changes=defaultdict(list)
  for v in rows:
   node=v['host_node'];fid=v['flow_id'];time=v['time_ns'];key=node,time
   if v['event'] not in ['sent','utilization_sample','utilization_report']:continue
   snapshots[key].add(v['host_data_payload_bytes'])
   if v['event']=='sent':
    state[node,fid]=v;allocation=(time,v['set_change'])
    if group_key.get(node)!=allocation or fid in group[node]:group[node]=[];group_key[node]=allocation
    group[node].append(fid);active[node]=set(group[node])
    if v['set_change']=='utilization_width':changes[key].append(v)
   elif v['event']=='utilization_report':
    assert received_grants[fid,v['utilization_report_generation']]<=time and v['serialized_bytes']>0
    state[node,fid]=v;checks['reports']+=1
   else:
    assert len(active[node])==v['active_flows'];assert key not in samples;samples[key]=v
    ready=[]
    for candidate in active[node]:
     s=state[node,candidate];first=s['utilization_high_first_generation'];generation=s['utilization_report_generation'];issued=s['utilization_issued_generation'];age=time-s['utilization_report_time_ns'];threshold=v['line_rate_bps']*90//100
     if s['grant_rate_bps']>=threshold and first>0 and first<=generation<=issued and s['utilization_report_ready'] and s['utilization_report_rate_bps']>=threshold and s['utilization_report_time_ns']>0 and 0<=age<=2*rtts[candidate]:ready.append(candidate)
    assert bool(ready)==bool(v['utilization_fabric_ready']),(st,node,time,ready,v)
    promote=not v['utilization_wide'] and v['utilization_low_windows']==2 and bool(ready)
    demote=bool(v['utilization_wide']) and v['utilization_high_windows']==2
    blocked=not v['utilization_wide'] and v['utilization_low_windows']==2 and not ready
    nodes[node]['checks']+=1;nodes[node]['promotions']+=int(promote);nodes[node]['demotions']+=int(demote);nodes[node]['blocked']+=int(blocked)
    decisions.append(dict(node=node,time_ns=time,promote=promote,demote=demote,blocked=blocked,ready_flows=ready))
  for v in decisions:
   key=v['node'],v['time_ns'];s=samples[key];dt=s['utilization_interval_ns'];assert dt in [4160,8320]
   prev=samples.get((v['node'],v['time_ns']-dt));baselines={prev['host_data_payload_bytes']} if prev else snapshots[v['node'],v['time_ns']-dt]
   good=[x for x in baselines if (s['host_data_payload_bytes']-x)*8000000000//dt==s['utilization_payload_bps']];assert len(good)==1
   rate=s['utilization_payload_bps'];assert bool(s['utilization_low_windows'])==(rate<s['line_rate_bps']*7//10);assert bool(s['utilization_high_windows'])==(rate>=s['line_rate_bps']*85//100)
   for field in ['utilization_low_windows','utilization_high_windows']:
    if s[field]==2:assert prev is not None and prev[field]>=1
   assert bool(changes.get(key))==(v['promote'] or v['demote'])
   if v['promote'] or v['demote']:assert len(changes[key])==s['active_flows'] and all(x['utilization_wide']==int(v['promote']) for x in changes[key])
  for node,s in stats(on).items():
   for k in ['checks','promotions','demotions']:assert s[k]==nodes[node][k]
  for line in next(Path(on['output_dir']).glob('*guard_stats.txt')).read_text().splitlines():
   if line.startswith('guard_utilization_feedback '):
    z=line.split()[1:];s={k:int(v) for k,v in zip(z[::2],z[1::2])};assert s['blocked']==nodes[s['node']]['blocked']
  assert checks['reports']==on['stats']['guard_cap_reports_received']
  out[st]=dict(trace_neutral=True,all_gate_checks_verified=True,cap_omissions=0,grant_pairs=pairs,report_records=checks['reports'],sample_windows=len(samples),counters={str(k):dict(v) for k,v in nodes.items()},decisions=decisions,scope='Replay of all receiver-visible gate decisions and rate windows; sender readiness encoding is checked by source and wire unit, not a complete sender event log')
  print(st,'verified',len(samples),'actual windows;',checks['reports'],'real reports;',sum(x['promotions'] for x in nodes.values()),'promotions;',sum(x['blocked'] for x in nodes.values()),'blocked opportunities',flush=True)
 (ROOT/'feedback_validation.json').write_text(json.dumps(out,indent=2)+'\n')
if __name__=='__main__':main()
