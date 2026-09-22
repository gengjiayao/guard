"""Validate trace neutrality, actual wire volume, and timeout flight state."""
import csv
import json
import re
from collections import Counter,defaultdict
from pathlib import Path
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

ROOT=Path(__file__).resolve().parents[1]
PROFILES=['joint32_l10','shared_l10','l10_ack1','l10_last','l10_ack1_last']
LABELS=['Joint32 λ1','ACK8, omit last','ACK1, omit last','ACK8, keep last','ACK1, keep last']

def main():
    a=json.loads((ROOT/'analysis.json').read_text())
    idx={r['arm']:r for r in a['runs'] if r['study']=='allreduce_dp2'}
    results=[]
    for profile in PROFILES:
        left='diagnosis_retry_'+profile;right=left+'_trace'
        original_trace=right
        if profile in ['l10_ack1','l10_ack1_last']:
            right='trace_sparse_'+profile+'_trace_full'
        x,y=idx[left],idx[right]
        neutral=x['fct_sha256']==y['fct_sha256'] and x['metrics']==y['metrics']
        rec=json.loads((ROOT/'runs'/y['key']/'result.json').read_text())
        d=Path(rec['output_dir']);path=next(d.glob('*controller.csv'))
        lines=path.read_text().splitlines();footer=[v for v in lines if v.startswith('#')]
        attempted,written,truncated=map(int,re.findall(r'\d+',footer[0]))
        sampled=int(re.search(r'sampled_out=(\d+)',footer[1]).group(1))
        assert attempted==written+sampled+truncated
        rows=list(csv.DictReader(v for v in lines if not v.startswith('#')))
        assert len(rows)==written
        completes=[v for v in rows if v['event_type']=='complete']
        complete_ids=Counter(int(v['flow_id']) for v in completes)
        assert all(n==1 for n in complete_ids.values())
        timeouts=[v for v in rows if v['event_type']=='timeout_probe']
        if truncated==0:
            assert set(complete_ids)==set(range(1280))
            assert len(timeouts)==y['metrics']['timeout_recoveries']
        inp=np.loadtxt(rec['flow'],skiprows=1)
        fct=np.loadtxt(y['fct_file'],dtype=np.int64)
        for v in completes:
            fid=int(v['flow_id']);flow=inp[fid]
            match=fct[(fct[:,0]==flow[0])&(fct[:,1]==flow[1])&(fct[:,4]==flow[3])&(abs(fct[:,5]-round(flow[4]*1e9))<=2)]
            assert len(match)==1 and int(v['time_ns'])==int(match[0,5]+match[0,6])
        classified=[]
        for v in timeouts:
            outstanding=int(v['snd_nxt'])-int(v['snd_una'])
            assert outstanding>=0
            assert (v['binding']=='empty_flight')==(outstanding==0)
            classified.append(dict(flow_id=int(v['flow_id']),time_ns=int(v['time_ns']),
                outstanding_bytes=outstanding,unsent_bytes=int(inp[int(v['flow_id']),3])-int(v['snd_nxt']),
                next_avail_delta_ns=int(v['next_avail_ns'])-int(v['time_ns']),
                rate_bps=int(v['final_rate_bps']),row=v))
        wire=list(csv.DictReader(Path(str(path)+'.wire.csv').open()))
        protocol=defaultdict(lambda:dict(packets=0,serialized_bytes=0))
        hosts=set()
        for v in wire:
            node=int(v['node_id']);proto=int(v['l3_protocol']);hosts.add(node)
            assert 0<=node<16 and 0<=proto<256
            for k in ['packets','serialized_bytes']:protocol[proto][k]+=int(v[k])
        assert hosts==set(range(16))
        assert protocol[17]['packets']>=32000000
        assert protocol[249]['packets']==y['metrics']['grants']
        total=sum(v['serialized_bytes'] for v in protocol.values())
        original_path=next(Path(idx[original_trace]['output_dir']).glob('*controller.csv'))
        original_footer=[v for v in original_path.read_text().splitlines() if v.startswith('#')]
        original_cap_omissions=int(re.findall(r'\d+',original_footer[0])[2])
        result=dict(profile=profile,selected_trace_arm=right,original_trace_arm=original_trace,
            original_cap_omissions=original_cap_omissions,trace_neutral=neutral,trace_rows=written,
            cap_omissions=truncated,complete_events=len(completes),timeouts=classified,
            total_serialized_bytes=total,protocol=dict(protocol),
            control_byte_fraction=(total-protocol[17]['serialized_bytes'])/total,
            fct_sha256=x['fct_sha256'],metrics=x['metrics'])
        results.append(result)
        print(profile,'neutral',neutral,'complete',len(completes),'cap_omissions',truncated,
              'timeouts',len(timeouts),'empty',sum(t['outstanding_bytes']==0 for t in classified),
              'protocol',dict(protocol))
    (ROOT/'diagnostic_analysis.json').write_text(json.dumps(results,indent=2)+'\n')
    fig,axes=plt.subplots(2,2,figsize=(12,8))
    x=np.arange(len(results));bottom=np.zeros(len(results))
    for proto,name in [(17,'Data'),(252,'ACK'),(249,'Rate grants')]:
        vals=np.array([r['protocol'].get(proto,{}).get('serialized_bytes',0)/1e9 for r in results])
        axes[0,0].bar(x,vals,bottom=bottom,label=name);bottom+=vals
    axes[0,0].set_ylabel('Host serialized packet bytes (GB)');axes[0,0].legend(fontsize=8)
    for ax,key,label,scale in [(axes[0,1],'fct_mean_us','Mean FCT (ms)',.001),(axes[1,0],'span_ms','Trace span (ms)',1)]:
        ax.bar(x,[r['metrics'][key]*scale for r in results]);ax.set_ylabel(label)
    empty=[sum(t['outstanding_bytes']==0 for t in r['timeouts']) for r in results]
    outstanding=[len(r['timeouts'])-v for r,v in zip(results,empty)]
    axes[1,1].bar(x,empty,label='No outstanding bytes')
    axes[1,1].bar(x,outstanding,bottom=empty,label='Outstanding bytes')
    axes[1,1].set_ylabel('Observed timeout events');axes[1,1].legend(fontsize=8)
    for ax in axes.flat:
        ax.set_xticks(x,LABELS,rotation=25,ha='right');ax.grid(axis='y',alpha=.2)
    fig.suptitle('Full DP2; development seed 301; serialized bytes include headers and exclude IFG')
    fig.tight_layout()
    for ext in ['png','pdf']:fig.savefig(ROOT/'figures'/('timeout_wire_diagnosis.'+ext),dpi=160)
    plt.close(fig)
    assert all(r['trace_neutral'] for r in results),'observation changed results; keep evidence and investigate'
    assert all(r['cap_omissions']==0 for r in results),'trace incomplete; preserve and repeat with larger cap'

if __name__=='__main__':main()
