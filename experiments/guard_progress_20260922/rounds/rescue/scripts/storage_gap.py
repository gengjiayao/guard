"""Decompose the full mean-FCT gap into original, exhaustive size bins."""
import json
from pathlib import Path
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
ROOT=Path(__file__).resolve().parents[1]
def main():
    a=json.loads((ROOT/'analysis.json').read_text());idx={(r['study'],r['arm']):r for r in a['runs']}
    edges=[0,4000,8000,16000,32000,64000,128000,256000,2000000,float('inf')];labels=['≤4K','4–8K','8–16K','16–32K','32–64K','64–128K','128–256K','256K–2M','>2M']
    results={};fig,axs=plt.subplots(1,2,figsize=(14,6))
    def flows(study,arm):
        r=idx[study,arm];rec=json.loads((ROOT/'runs'/r['key']/'result.json').read_text());v=np.loadtxt(r['fct_file'],ndmin=2)
        v=v[v[:,5]>int((2+rec['warmup'])*1e9)];return r,v
    for ax,study,title in zip(axs,['ali30','ali50'],['Storage30','Storage50']):
        gr,g=flows(study,'scenes_shared_rescue');hr,h=flows(study,'baselines_homa')
        assert len(g)==len(h);n=len(g);rows=[]
        for lo,hi,label in zip(edges[:-1],edges[1:],labels):
            gg=g[(g[:,4]>lo)&(g[:,4]<=hi),6]/1000;hh=h[(h[:,4]>lo)&(h[:,4]<=hi),6]/1000;assert len(gg)==len(hh)
            row=dict(label=label,n=len(gg),guard_mean_us=float(gg.mean()) if len(gg) else None,homa_mean_us=float(hh.mean()) if len(hh) else None,
                mean_gap_contribution_us=float((gg.sum()-hh.sum())/n))
            rows.append(row)
        gap=gr['metrics']['fct_mean_us']-hr['metrics']['fct_mean_us'];assert abs(sum(r['mean_gap_contribution_us'] for r in rows)-gap)<1e-9
        vals=[r['mean_gap_contribution_us'] for r in rows];ax.bar(range(len(rows)),vals,color=['#b94040' if v>0 else '#167c67' for v in vals]);ax.axhline(0,color='black',lw=.7)
        ax.set_xticks(range(len(rows)),labels,rotation=45,ha='right');ax.set_ylabel('Contribution to mean FCT gap (µs)');ax.set_title(title+f': total GUARD − Homa = {gap:+.3f} µs');ax.grid(axis='y',alpha=.2)
        for i,(v,r) in enumerate(zip(vals,rows)):ax.annotate(f"n={r['n']}",(i,v),xytext=(0,5 if v>=0 else -5),textcoords='offset points',ha='center',va='bottom' if v>=0 else 'top',fontsize=7)
        ax.margins(y=.2);results[study]=dict(eligible_flows=n,mean_gap_us=gap,bins=rows)
    fig.suptitle('Original eligible flows and all bins retained; development seed301\nPer-bin contributions sum to the complete average-latency gap; positive = GUARD slower')
    fig.tight_layout()
    for ext in ['png','pdf']:fig.savefig(ROOT/'figures'/('storage_gap_contributions.'+ext),dpi=160)
    plt.close(fig);(ROOT/'storage_gap_contributions.json').write_text(json.dumps(results,indent=2)+'\n')
    text='\n## Storage 平均 FCT 差距的来源\n\n'
    for study,r in results.items():
        largest=sorted((b for b in r['bins'] if b['mean_gap_contribution_us']>0),key=lambda b:b['mean_gap_contribution_us'],reverse=True)[:2]
        text+=f"- {study}：总体平均 FCT 差值（GUARD−Homa）为 {r['mean_gap_us']:.6f} µs；主要正向分量为 "+'、'.join(f"{v['label']} 字节区间（{v['n']} 条合格流，贡献 {v['mean_gap_contribution_us']:.6f} µs）" for v in largest)+'。\n'
    text+='\n这里按原 5 ms 预热规则保留全部合格流，逐区间计算总 FCT 差并除以合格流总数，所有区间之和严格等于总均值差；没有删去少数长流。该分解用于确定后续源码诊断对象，不单独证明控制机制的因果关系。图见 figures/storage_gap_contributions.pdf。\n'
    with (ROOT/'REPORT.zh.md').open('a') as f:f.write(text)
    print('Validated exhaustive Storage mean-gap decomposition; wrote one figure')
if __name__=='__main__':main()
