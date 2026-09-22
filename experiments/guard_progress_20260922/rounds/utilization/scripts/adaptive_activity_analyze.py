"""Validate DATA conservation and characterize observed grant intervals/readiness."""
import csv,json,re
from pathlib import Path
from collections import defaultdict,Counter,deque
import numpy as np
ROOT=Path(__file__).resolve().parents[1]
def load_csv(path):
 lines=path.read_text().splitlines();return list(csv.DictReader(l for l in lines if not l.startswith('#'))),[l for l in lines if l.startswith('#')]
def quantiles(v):return {str(p):float(np.percentile(v,p)) for p in [0,10,25,50,75,90,95,99,100]} if v else {}
def main():
 a=json.loads((ROOT/'analysis.json').read_text());idx={(r['study'],r['arm']):r for r in a['runs']};out={}
 for st in ['ali30','ali50']:
  r=idx[st,'width_trace_adaptive_activity_trace'];rec=json.loads((ROOT/'runs'/r['key']/'result.json').read_text());flow=np.loadtxt(rec['flow'],skiprows=1)
  config=Path(rec['config']).read_text();mtu=int(re.search(r'^PACKET_PAYLOAD_SIZE\s+(\d+)',config,re.M).group(1))
  expected_bytes=Counter();expected_packets=Counter()
  for f in flow:expected_bytes[int(f[1])]+=int(f[3]);expected_packets[int(f[1])]+=(int(f[3])+mtu-1)//mtu
  path=next(Path(r['output_dir']).glob('*grants.csv'));rx,_=load_csv(Path(str(path)+'.rx.csv'))
  for v in rx:
   node=int(v['node_id']);assert int(v['nics'])==1
   assert int(v['payload_bytes'])==expected_bytes[node],(st,node,v,expected_bytes[node])
   assert int(v['packets'])==expected_packets[node],(st,node,v,expected_packets[node])
  assert set(expected_bytes)<=set(int(v['node_id']) for v in rx)
  rows,footer=load_csv(path);groups=defaultdict(list)
  for v in rows:
   for k in v:
    if k not in ['event','set_change']:v[k]=int(v[k])
   groups[v['flow_id']].append(v)
  controller=next(Path(r['output_dir']).glob('*controller.csv'));crows,cfooter=load_csv(controller)
  attempted,written,truncated=map(int,re.findall(r'\d+',cfooter[0]));sampled=int(re.search(r'sampled_out=(\d+)',cfooter[1]).group(1))
  assert attempted==written+sampled and truncated==0 and written==len(crows)
  selected={i for i,f in enumerate(flow) if f[3]>=256001};eligible={i for i in selected if flow[i,4]>2+rec['warmup']}
  completed=[v for v in crows if v['event_type']=='complete'];counts=Counter(int(v['flow_id']) for v in completed)
  assert set(counts)==selected and all(v==1 for v in counts.values())
  fct=np.loadtxt(r['fct_file'],dtype=np.int64);ends=defaultdict(list)
  for v in fct:ends[int(v[0]),int(v[1]),int(v[4]),int(v[5])].append(int(v[5]+v[6]))
  for v in completed:
   fid=int(v['flow_id']);f=flow[fid];start=round(f[4]*1e9);possible=[]
   for delta in range(-2,3):possible+=ends[int(f[0]),int(f[1]),int(f[3]),start+delta]
   assert int(v['time_ns']) in possible
  post_sync={(int(v['flow_id']),int(v['time_ns'])):v for v in crows if v['event_type']=='grant'}
  intervals=[];observations=[]
  for fid in sorted(eligible):
   sends=[v for v in groups[fid] if v['event']=='sent'];receives=[v for v in groups[fid] if v['event']=='received'];pending=defaultdict(deque)
   for v in sends:pending[v['generation'],v['grant_rate_bps']].append(v)
   for v in receives:
    s=pending[v['generation'],v['grant_rate_bps']].popleft();assert s['time_ns']<=v['time_ns']
    if s['distinct_senders']<2 or s['grant_rate_bps']<s['line_rate_bps']*.5 or s['set_change']=='release':continue
    c=post_sync.get((fid,v['time_ns']))
    observations.append(dict(flow_id=fid,time_ns=v['time_ns'],pre_sync_ready=v['sender_pre_sync_ready'],paused=v['sender_paused'],window_bound=v['sender_window_bound'],pacing_future=v['sender_next_avail_ns']>v['time_ns'],pre_sync_pacing_delay_ns=max(0,v['sender_next_avail_ns']-v['time_ns']),post_sync_pacing_delay_ns=None if c is None else max(0,int(c['next_avail_ns'])-int(c['time_ns'])),shorter_ready_other_destination=v['sender_shorter_ready_other_destination'],sender_active_flows=v['sender_active_flows'],sender_ready_flows=v['sender_ready_flows'],fabric_cap_below_grant=v['sender_fabric_rate_bps']<v['grant_rate_bps'],sampled_post_sync_binding=None if c is None else c['binding']))
   assert all(not q for q in pending.values())
   for u,v in zip(sends,sends[1:]):
    dt=v['time_ns']-u['time_ns'];assert dt>=0 and v['host_data_payload_bytes']>=u['host_data_payload_bytes'] and v['receiver_seq']>=u['receiver_seq']
    if dt<8320 or u['set_change']=='release':continue
    if u['distinct_senders']<2:continue
    aggregate=8*(v['host_data_payload_bytes']-u['host_data_payload_bytes'])/dt
    own=8*(v['receiver_seq']-u['receiver_seq'])/dt
    category='high' if u['grant_rate_bps']>=u['line_rate_bps']*.5 else 'low' if u['grant_rate_bps']<=100000000 else 'middle'
    intervals.append(dict(flow_id=fid,receiver=u['host_node'],start_ns=u['time_ns'],end_ns=v['time_ns'],duration_ns=dt,grant_gbps=u['grant_rate_bps']/1e9,category=category,receiver_payload_gbps=aggregate,flow_progress_gbps=own,active_flows=u['active_flows'],distinct_senders=u['distinct_senders']))
  categories={}
  for cat in ['high','middle','low']:
   x=[v for v in intervals if v['category']==cat];total=sum(v['duration_ns'] for v in x)
   categories[cat]=dict(interval_count=len(x),total_interval_ns=total,duration_us_quantiles=quantiles([v['duration_ns']/1000 for v in x]),receiver_payload_gbps_quantiles=quantiles([v['receiver_payload_gbps'] for v in x]),own_progress_gbps_quantiles=quantiles([v['flow_progress_gbps'] for v in x]),interval_duration_weighted_below50_fraction=sum(v['duration_ns'] for v in x if v['receiver_payload_gbps']<50)/total if total else None,interval_duration_weighted_below80_fraction=sum(v['duration_ns'] for v in x if v['receiver_payload_gbps']<80)/total if total else None)
  obs_summary=dict(count=len(observations),pre_sync_ready_fraction=float(np.mean([v['pre_sync_ready'] for v in observations])),paused_fraction=float(np.mean([v['paused'] for v in observations])),window_bound_fraction=float(np.mean([v['window_bound'] for v in observations])),pacing_future_fraction=float(np.mean([v['pacing_future'] for v in observations])),shorter_ready_other_destination_fraction=float(np.mean([v['shorter_ready_other_destination']>0 for v in observations])),fabric_cap_below_grant_fraction=float(np.mean([v['fabric_cap_below_grant'] for v in observations])),pre_sync_pacing_delay_us_quantiles=quantiles([v['pre_sync_pacing_delay_ns']/1000 for v in observations]),post_sync_pacing_delay_us_quantiles=quantiles([v['post_sync_pacing_delay_ns']/1000 for v in observations if v['post_sync_pacing_delay_ns'] is not None]),sampled_post_sync_bindings=dict(Counter(v['sampled_post_sync_binding'] or 'not_sampled' for v in observations)))
  out[st]=dict(data_conservation=True,host_count=len(rx),payload_bytes=sum(expected_bytes.values()),packets=sum(expected_packets.values()),selected_flows=len(selected),eligible_flows=len(eligible),controller_rows=written,controller_cap_omissions=truncated,controller_completions=len(completed),categories=categories,sender=obs_summary,intervals=intervals,sender_observations=observations)
  print(st,'DATA conservation exact; categories',categories,'sender',obs_summary,flush=True)
 (ROOT/'adaptive_activity_analysis.json').write_text(json.dumps(out,indent=2)+'\n')
if __name__=='__main__':main()
