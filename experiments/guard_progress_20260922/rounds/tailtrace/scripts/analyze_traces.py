"""Read sampled event states; report samples rather than exact residency times."""
import csv
import json
from collections import defaultdict
from pathlib import Path
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
ROOT=Path(__file__).resolve().parents[1]

def main():
    runs=[]
    fig,ax=plt.subplots(figsize=(7,4))
    for p in sorted((ROOT/'runs').glob('*/result.json')):
        r=json.loads(p.read_text())
        if r['status']!='completed':continue
        out=Path(r['output_dir'])
        fct=np.loadtxt(next(out.glob('*_out_fct.txt')),dtype=np.int64,ndmin=2)
        if r['arm'].startswith(('causal_', 'scheduler_')):
            ax.plot(np.sort(fct[:,6])/1e6,np.arange(1,len(fct)+1)/len(fct),label=r['arm'].replace('causal_','').replace('scheduler_',''))
        paths=list(out.glob('*controller.csv'))
        if not paths:continue
        lines=paths[0].read_text().splitlines()
        footer=[l for l in lines if l.startswith('#')]
        data=list(csv.DictReader(l for l in lines if not l.startswith('#')))
        byflow=defaultdict(list)
        for row in data:byflow[int(row['flow_id'])].append(row)
        inputs=np.loadtxt(r['flow'],skiprows=1,ndmin=2)
        assert len(byflow)==len(inputs), 'sampling cap omitted entire flows'
        completed=[v for v in data if v['event_type']=='complete']
        assert len(completed)==len(inputs), 'sampling cap omitted completions'
        flowstats=[]
        for fid,rows in byflow.items():
            inp=inputs[fid]
            expected_start=round(inp[4]*1e9)
            match=fct[(fct[:,0]==inp[0])&(fct[:,1]==inp[1])&(abs(fct[:,5]-expected_start)<=2)]
            assert len(match)==1
            row=match[0]
            a=np.array([[float(v[k]) for k in ['time_ns','snd_nxt','snd_una','final_rate_bps','grant_rate_bps','window_bytes','tx_bytes']] for v in rows])
            completion=[v for v in rows if v['event_type']=='complete']
            assert len(completion)==1
            ci=rows.index(completion[0])
            assert all(v['time_ns']==completion[0]['time_ns'] for v in rows[ci+1:]), 'post-completion event changed simulated time'
            a=a[:ci+1]
            assert abs(a[-1,0]-row[5]-row[6])<=1
            assert a[-1,1]==a[-1,2]==inp[3]
            # No assumption of rates remaining constant between sparse samples.
            rates=a[:,3]/1e9
            flowstats.append(dict(flow_id=fid,src=int(inp[0]),dst=int(inp[1]),start_ns=int(row[5]),fct_ms=row[6]/1e6,
                samples=len(a),sample_rate_median_gbps=float(np.median(rates)),sample_fraction_rate_below_1g=float(np.mean(rates<1)),
                sample_fraction_window_full=float(np.mean(a[:,1]-a[:,2]>=a[:,5])),sample_fraction_grant_100g=float(np.mean(a[:,4]>=100e9)),
                max_sample_gap_us=float(np.diff(a[:,0]).max()/1000) if len(a)>1 else 0,
                tx_bytes_at_completion=int(a[-1,6])))
        flowstats.sort(key=lambda v:v['fct_ms'],reverse=True)
        summary=dict(key=r['key'],rows=len(data),complete_events=len(completed),footer=footer,flowstats=flowstats)
        runs.append(summary)
        # Three globally slowest flows, selected by complete FCT, retain full traces.
        f,axs=plt.subplots(2,1,figsize=(8,5.5),sharex=True)
        for st in flowstats[:3]:
            rows=byflow[st['flow_id']]
            x=np.array([int(v['time_ns']) for v in rows])/1e6-st['start_ns']/1e6
            axs[0].plot(x,[int(v['snd_nxt'])/1e6 for v in rows],label=f"Flow {st['flow_id']}, {st['src']}→{st['dst']}")
            axs[1].step(x,[int(v['final_rate_bps'])/1e9 for v in rows],where='post')
        axs[0].set_ylabel('Sent payload (MB)');axs[0].legend(fontsize=8)
        axs[1].set_ylabel('Sampled rate cap (Gbps)');axs[1].set_yscale('log');axs[1].set_ylim(.08,150);axs[1].set_xlabel('Time since flow start (ms)')
        f.suptitle(r['arm']+'; three slowest flows, development seed 301',fontsize=10)
        f.tight_layout();f.savefig(ROOT/'figures'/(r['arm']+'_slowflows.png'),dpi=160);f.savefig(ROOT/'figures'/(r['arm']+'_slowflows.pdf'));plt.close(f)
    ax.set(xlabel='Flow completion time (ms)',ylabel='CDF',title='Full DP2 causal probes; development seed 301')
    ax.legend(fontsize=7);ax.grid(alpha=.2);fig.tight_layout();fig.savefig(ROOT/'figures/causal_cdf.png',dpi=160);fig.savefig(ROOT/'figures/causal_cdf.pdf');plt.close(fig)
    (ROOT/'trace_analysis.json').write_text(json.dumps(runs,indent=2)+'\n')
    print('Validated',len(runs),'complete per-flow trace sets')
    for r in runs:print(r['key'],r['rows'],r['footer'],r['flowstats'][:3])

if __name__=='__main__':
    (ROOT/'figures').mkdir(exist_ok=True)
    main()
