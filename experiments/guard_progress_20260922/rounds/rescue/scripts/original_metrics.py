"""Retain original fairness and Ring questions instead of substituting generic summaries."""
import json
from pathlib import Path
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
ROOT=Path(__file__).resolve().parents[1]
def main():
    a=json.loads((ROOT/'analysis.json').read_text());idx={(r['study'],r['arm']):r for r in a['runs']}
    arms=['scenes_shared_rescue','baselines_hpcc','baselines_homa','baselines_dcqcn','baselines_timely'];names=['GUARD','HPCC','Homa','DCQCN','TIMELY']
    colors=['#0072B2','#D55E00','#009E73','#CC79A7','#555555'];styles=['-','--','-.',':']
    def save(fig,name):
        fig.tight_layout()
        for ext in ['png','pdf']:fig.savefig(ROOT/'figures'/(name+'.'+ext),dpi=160)
        plt.close(fig)
    fig,axs=plt.subplots(2,3,figsize=(14,8));fair={}
    for ax,arm,name in zip(axs.flat,arms,names):
        r=idx['fairness',arm];v=np.loadtxt(next(Path(r['output_dir']).glob('*_flow_bw.txt')),ndmin=2)
        fct=np.loadtxt(r['fct_file'],ndmin=2)
        assert np.all(fct[:,5]<=2010000000) and np.all(fct[:,5]+fct[:,6]>2012000000), 'Common fairness window no longer has all flows active'
        means=[]
        for src in range(4):
            z=v[v[:,1]==src];grid=np.zeros(650);indices=np.rint(z[:,0]/100000).astype(int)-1
            valid=(indices>=0)&(indices<len(grid));assert len(np.unique(indices[valid]))==sum(valid)
            grid[indices[valid]]=z[valid,5];ax.stairs(grid,np.arange(651)*.1,color=colors[src],ls=styles[src],label='Sender '+str(src))
            means.append(float(grid[100:120].mean()))
        means=np.array(means);j=float(means.sum()**2/(4*np.sum(means**2)));fair[name]=dict(jain_10_12ms=j,mean_sender_rates_gbps=means.tolist(),flow_bw_file=str(next(Path(r['output_dir']).glob('*_flow_bw.txt'))))
        ax.set(title=name,xlabel='Time (ms)',ylabel='Send rate (Gb/s)',xlim=(0,65),ylim=(0,105));ax.grid(alpha=.2)
    axs[0,0].legend(fontsize=8,ncol=2)
    ax=axs.flat[-1];ax.scatter(range(5),[fair[n]['jain_10_12ms'] for n in names],c=colors)
    for i,n in enumerate(names):ax.annotate(f"{fair[n]['jain_10_12ms']:.5f}",(i,fair[n]['jain_10_12ms']),xytext=(0,5),textcoords='offset points',ha='center')
    ax.set_xticks(range(5),names,rotation=30);ax.set(ylabel='Jain index, original10–12ms window',ylim=(0,1.08));ax.grid(alpha=.2)
    fig.suptitle('Original fairness plot: zero-filled100µs sender samples; development seed301');save(fig,'original_fairness')
    fig,axs=plt.subplots(1,3,figsize=(14,5));ring={}
    for ax,k,label in zip(axs,['span_ms','drops','timeout_recoveries'],['Trace span (ms)','Dropped packets','Generic timeout recoveries']):
        vals=[]
        for arm,name in zip(arms,names):
            r=idx['ring',arm];val=r['metrics'][k];vals.append(val);ring.setdefault(name,{})[k]=val
            ring[name]['homa_native_resends']=r['stats'].get('homa_resends_sent',0)
        ax.bar(range(5),vals,color=colors);ax.set_xticks(range(5),names,rotation=30);ax.set_ylabel(label);ax.grid(axis='y',alpha=.2)
        if k!='span_ms':ax.set_yscale('symlog',linthresh=1);ax.set_ylim(0,max(vals)*3+1)
        else:ax.set_ylim(0,max(vals)*1.2)
        for i,v in enumerate(vals):ax.annotate(f'{v:.3f}' if k=='span_ms' else str(v),(i,v),xytext=(0,3),textcoords='offset points',ha='center',fontsize=8)
    fig.suptitle(f"Original Ring metrics; development seed301; Homa native RESENDs: {ring['Homa']['homa_native_resends']}");save(fig,'original_ring')
    (ROOT/'original_metrics.json').write_text(json.dumps(dict(fairness=fair,ring=ring),indent=2)+'\n')
    text='\n## 公平性与 Ring 原图的专门指标\n\n'
    for name in names:text+=f"- {name}：原 10–12 ms 公共区间 Jain 指数 {fair[name]['jain_10_12ms']:.6f}；Ring 跨度 {ring[name]['span_ms']:.6f} ms，丢包 {ring[name]['drops']}，通用超时恢复 {ring[name]['timeout_recoveries']}。\n"
    text+=f"\nHoma 的 Ring 原生 RESEND 为 {ring['Homa']['homa_native_resends']} 次，独立于通用恢复计数。公平性沿用原 100 µs 栅格补零，并核对公共区间内四条流均未完成；没有用平均 FCT 替代公平性指标。图见 figures/original_fairness.pdf 与 original_ring.pdf，数据见 original_metrics.json。这些仍是开发样本，不是独立确认。\n"
    with (ROOT/'REPORT.zh.md').open('a') as f:f.write(text)
    print('Validated original fairness interval and Ring metrics; wrote two figures')
if __name__=='__main__':main()
