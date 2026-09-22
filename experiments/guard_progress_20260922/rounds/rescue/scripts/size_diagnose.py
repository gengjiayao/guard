"""Verify observation-only filtering and classify large Storage flow cap samples."""
import csv,json,re
from collections import defaultdict,Counter
from pathlib import Path
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
ROOT=Path(__file__).resolve().parents[1]
def main():
    a=json.loads((ROOT/'analysis.json').read_text());idx={(r['study'],r['arm']):r for r in a['runs']};results={}
    for study in ['ali30','ali50']:
        parent=idx[study,'scenes_shared_rescue'];x=idx[study,'size_trace_shared_rescue'];y=idx[study,'size_trace_shared_large_trace']
        assert parent['fct_sha256']==x['fct_sha256']==y['fct_sha256']
        assert parent['metrics']==x['metrics']==y['metrics']
        rec=json.loads((ROOT/'runs'/y['key']/'result.json').read_text());inp=np.loadtxt(rec['flow'],skiprows=1);fct=np.loadtxt(y['fct_file'],dtype=np.int64)
        path=next(Path(y['output_dir']).glob('*controller.csv'));lines=path.read_text().splitlines();foot=[l for l in lines if l.startswith('#')]
        attempted,written,truncated=map(int,re.findall(r'\d+',foot[0]));sampled=int(re.search(r'sampled_out=(\d+)',foot[1]).group(1))
        filtered,minimum=map(int,re.findall(r'\d+',foot[2]));assert minimum==256001 and filtered>0
        assert attempted==written+sampled and truncated==0
        rows=list(csv.DictReader(l for l in lines if not l.startswith('#')));assert len(rows)==written
        expected={i for i,flow in enumerate(inp) if flow[3]>=minimum};group=defaultdict(list)
        for v in rows:
            fid=int(v['flow_id']);assert fid in expected;group[fid].append(v)
        complete=[v for v in rows if v['event_type']=='complete'];counts=Counter(int(v['flow_id']) for v in complete)
        assert set(counts)==expected and all(v==1 for v in counts.values())
        completion_lookup=defaultdict(list)
        for v in fct:completion_lookup[int(v[0]),int(v[1]),int(v[4]),int(v[5])].append(int(v[5]+v[6]))
        for v in complete:
            fid=int(v['flow_id']);flow=inp[fid];start=round(flow[4]*1e9);end=int(v['time_ns'])
            possible=[]
            for delta in range(-2,3):possible+=completion_lookup[int(flow[0]),int(flow[1]),int(flow[3]),start+delta]
            assert end in possible
        eligible={i for i in expected if inp[i,4]>(2+rec['warmup'])};observed=[]
        for fid in sorted(eligible):
            samples=[v for v in group[fid] if v['event_type'] in ['grant','hpcc']]
            if not samples:continue
            fabric=np.array([int(v['hpcc_rate_bps']) for v in samples]);grant=np.array([int(v['grant_rate_bps']) for v in samples]);rate=np.array([int(v['final_rate_bps']) for v in samples])
            time=np.array([int(v['time_ns']) for v in samples]);next_avail=np.array([int(v['next_avail_ns']) for v in samples]);flight=np.array([int(v['snd_nxt'])-int(v['snd_una']) for v in samples]);win=np.array([int(v['window_bytes']) for v in samples])
            observed.append(dict(flow_id=fid,n_samples=len(samples),fabric_binding_fraction=float(np.mean([v['binding']=='reactive' for v in samples])),receiver_binding_fraction=float(np.mean([v['binding']=='grant' for v in samples])),tie_fraction=float(np.mean([v['binding']=='tie' for v in samples])),
                fabric_cap_lower_fraction=float(np.mean(fabric<grant)),receiver_cap_lower_fraction=float(np.mean(grant<fabric)),
                receiver_selected_below_line_fraction=float(np.mean([(v['binding']=='grant' and int(v['final_rate_bps'])<100000000000) for v in samples])),
                fabric_selected_below_line_fraction=float(np.mean([(v['binding']=='reactive' and int(v['final_rate_bps'])<100000000000) for v in samples])),
                below1Gbps_sample_fraction=float(np.mean(rate<1e9)),window_full_sample_fraction=float(np.mean(flight>=win)),ready_sample_fraction=float(np.mean(next_avail<=time)),
                fabric_rate_median_gbps=float(np.median(fabric)/1e9),grant_rate_median_gbps=float(np.median(grant)/1e9)))
        assert len(observed)==len(eligible)
        result=dict(trace_neutral=True,min_flow_bytes=minimum,size_filtered_events=filtered,trace_rows=written,cap_omissions=truncated,
            selected_all_flows=len(expected),selected_eligible_flows=len(eligible),completed_events=len(complete),per_flow=observed,
            mean_per_flow_fabric_binding_fraction=float(np.mean([v['fabric_binding_fraction'] for v in observed])),
            mean_per_flow_receiver_binding_fraction=float(np.mean([v['receiver_binding_fraction'] for v in observed])),
            mean_per_flow_tie_fraction=float(np.mean([v['tie_fraction'] for v in observed])),
            mean_receiver_selected_below_line_fraction=float(np.mean([v['receiver_selected_below_line_fraction'] for v in observed])),
            mean_fabric_selected_below_line_fraction=float(np.mean([v['fabric_selected_below_line_fraction'] for v in observed])))
        results[study]=result;print(study,'complete selected',len(expected),'eligible',len(eligible),'no cap omissions; neutral; cap fractions',result['mean_per_flow_fabric_binding_fraction'],result['mean_per_flow_receiver_binding_fraction'])
    (ROOT/'size_diagnostic_analysis.json').write_text(json.dumps(results,indent=2)+'\n')
    fig,axs=plt.subplots(1,2,figsize=(12,5))
    for ax,(study,r) in zip(axs,results.items()):
        values=[r['mean_per_flow_fabric_binding_fraction'],r['mean_per_flow_receiver_binding_fraction'],r['mean_per_flow_tie_fraction']]
        ax.bar(['Fabric selected','Receiver selected','Equal caps'],np.array(values)*100);ax.set_ylabel('Mean per-flow sampled fraction (%)');ax.set_title(study+f"; {r['selected_eligible_flows']} eligible large flows");ax.set_ylim(0,100);ax.grid(axis='y',alpha=.2)
        for i,v in enumerate(values):ax.annotate(f'{v*100:.2f}%',(i,v*100),xytext=(0,4),textcoords='offset points',ha='center')
    fig.suptitle('Large-flow sampled controller selection; original complete Storage traffic\n10µs observation sampling; these fractions are not exact time shares');fig.tight_layout()
    for ext in ['png','pdf']:fig.savefig(ROOT/'figures'/('storage_cap_diagnosis.'+ext),dpi=160)
    plt.close(fig)
    text='\n## Storage 大消息速率限制诊断\n\n'
    for study,r in results.items():text+=f"- {study}：完整日志覆盖 {r['selected_all_flows']} 条被大小条件选中的流，其中 {r['selected_eligible_flows']} 条符合原预热规则。逐流控制路径采样点比例再取平均：网络上限被选中 {r['mean_per_flow_fabric_binding_fraction']*100:.2f}%，接收上限被选中 {r['mean_per_flow_receiver_binding_fraction']*100:.2f}%，上限相等 {r['mean_per_flow_tie_fraction']*100:.2f}%。同时低于 100 Gb/s 线速且选中接收上限的比例为 {r['mean_receiver_selected_below_line_fraction']*100:.2f}%，选中网络上限的比例为 {r['mean_fabric_selected_below_line_fraction']*100:.2f}%。\n"
    text+='\n日志过滤仅选择原始消息大小大于 256,000 字节的记录，实际流量和全部完成记录保持完整；新构建的无日志控制与上一构建以及同构建日志运行逐流 FCT、全部指标一致。全部被选择流均有匹配完成事件，没有行数上限遗漏。采样点比例不能解释为精确时间占比，路径选择标签沿用实际控制函数对尾部旁路的处理；选中接收上限不一定代表接收上限低于线速。这些记录不能单独证明全部延迟差距的因果来源。图见 figures/storage_cap_diagnosis.pdf。\n'
    with (ROOT/'REPORT.zh.md').open('a') as f:f.write(text)
if __name__=='__main__':main()
