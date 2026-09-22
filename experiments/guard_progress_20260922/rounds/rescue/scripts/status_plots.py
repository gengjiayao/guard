"""Audit the current global GUARD candidate against each same-build baseline."""
import json
from pathlib import Path
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.ticker import LogLocator, FuncFormatter, NullFormatter
ROOT=Path(__file__).resolve().parents[1]
def main():
    a=json.loads((ROOT/'analysis.json').read_text());idx={(r['study'],r['arm']):r for r in a['runs']}
    studies=['ali30','ali50','web40','fb40','fabric','receiver','hybrid','fairness','alltoall','allreduce_dp2','ring']
    snames=['Storage30','Storage50','Web','Analytics','Fabric','Receiver','Hybrid','Fairness','All-to-All','DP2','Ring']
    baseline=['homa','hpcc','dcqcn','timely'];bnames=['Homa','HPCC','DCQCN','TIMELY']
    keys=['fct_mean_us','slowdown_p99','span_ms','queue_worst_port_fixed_mean_us'];labels=['Mean FCT','P99 slowdown','Trace span','Worst-port mean queue']
    def row(study,arm):return idx[study,arm]
    def save(fig,name):
        fig.tight_layout()
        for ext in ['png','pdf']:fig.savefig(ROOT/'figures'/(name+'.'+ext),dpi=160)
        plt.close(fig)
    comparison={};fig,axs=plt.subplots(1,4,figsize=(17,7),sharey=True)
    for ax,k,label in zip(axs,keys,labels):
        values=[]
        for i,study in enumerate(studies):
            phase='dp2' if study=='allreduce_dp2' else 'baselines'
            g=row(study,('dp2' if study=='allreduce_dp2' else 'scenes')+'_shared_rescue')
            b=[row(study,phase+'_'+p) for p in baseline]
            best=min(b,key=lambda r:r['metrics'][k]);gv=g['metrics'][k];bv=best['metrics'][k]
            ratio=gv/bv if bv else None
            comparison.setdefault(study,{})[k]=dict(guard=gv,best_baseline=best['arm'].split('_')[-1],best_value=bv,ratio=ratio,
                pairwise_ratios={p:gv/r['metrics'][k] if r['metrics'][k] else None for p,r in zip(baseline,b)})
            if ratio is None:
                ax.text(1,i,'baseline zero',fontsize=8);continue
            values.append(ratio);color='#b94040' if ratio>1 else '#167c67';ax.scatter(ratio,i,color=color,s=45)
            ax.annotate(f'{ratio:.3g}× '+bnames[baseline.index(best['arm'].split('_')[-1])],(ratio,i),xytext=(5,0),textcoords='offset points',va='center',fontsize=8)
        ax.set_xscale('log');ax.set_xlim(min(min(values),1)*.7,max(max(values),1)*4);ax.axvline(1,color='gray',ls='--');ax.set_title(label);ax.set_xlabel('GUARD / lowest baseline');ax.grid(axis='x',alpha=.2)
        ax.xaxis.set_major_locator(LogLocator(base=10,subs=(1,2,5)))
        ax.xaxis.set_major_formatter(FuncFormatter(lambda x,pos:f'{x:g}'))
        ax.xaxis.set_minor_formatter(NullFormatter())
    axs[0].set_yticks(range(len(studies)),snames);axs[0].invert_yaxis();fig.suptitle('One Shared rescue configuration across all scenes; same-build development seed 301\nAbove 1 = worse observed value; no independent confirmation or statistical-tie claim');save(fig,'current_baseline_gaps')
    fig,axs=plt.subplots(2,4,figsize=(17,8))
    for i,study in enumerate(['ali30','ali50']):
        for j,k in enumerate(['mean','95','99','99.9']):
            ax=axs[i,j]
            for arm,name,style in [('scenes_shared_rescue','GUARD','-')]+[('baselines_'+p,n,'--') for p,n in zip(baseline,bnames)]:
                bins=row(study,arm)['bins'];ax.plot(range(len(bins)),[v[k] if v['n'] else np.nan for v in bins],label=name,ls=style,marker='o',ms=3)
            ax.set_xticks(range(len(bins)),['4K','8K','16K','32K','64K','128K','256K','2M','>2M'],rotation=45);ax.set_yscale('log');ax.set_title(snames[i]+' '+('mean' if k=='mean' else 'P'+k));ax.set_ylabel('FCT slowdown');ax.grid(alpha=.2)
    handles,leg=axs[0,0].get_legend_handles_labels();fig.legend(handles,leg,ncol=5,loc='upper center',bbox_to_anchor=(.5,.96));fig.suptitle('Storage: current GUARD and all four same-build baselines; development seed 301')
    fig.tight_layout(rect=(0,0,1,.9))
    for ext in ['png','pdf']:fig.savefig(ROOT/'figures'/('storage_baselines.'+ext),dpi=160)
    plt.close(fig)
    fig,axs=plt.subplots(1,3,figsize=(15,5))
    for ax,study,name in zip(axs,['web40','fb40','alltoall'],['Web','Analytics','All-to-All']):
        for arm,label in [('scenes_shared_rescue','GUARD')]+[('baselines_'+p,n) for p,n in zip(baseline,bnames)]:
            r=row(study,arm);record=json.loads((ROOT/'runs'/r['key']/'result.json').read_text());data=np.loadtxt(r['fct_file'],ndmin=2)
            data=data[data[:,5]>int((2+record['warmup'])*1e9)];x=np.sort(data[:,6]/1000)
            ax.plot(x,np.arange(1,len(x)+1)/len(x),label=label)
        ax.set_xscale('log');ax.set(xlabel='FCT (µs)',ylabel='CDF',title=name);ax.grid(alpha=.2)
    axs[0].legend(fontsize=8);fig.suptitle('Original eligible flows retained; same-build development seed 301');save(fig,'workload_baseline_cdfs')
    (ROOT/'current_baseline_gaps.json').write_text(json.dumps(comparison,indent=2)+'\n')
    text='\n## 当前统一配置与四基线的同构建复核\n\n'
    text+='补充测量十个非 DP2 原场景的四个基线共 40 次。下列固定使用 Shared rescue 配置，并按指标比较本场景中最低的基线实测值；这是开发样本比较，不能证明统计优势。公平性、Ring 和消融等原图还包含其他专门指标，下面四项汇总不能代替这些完整图的验收。\n\n'
    for study,name in zip(studies,snames):
        parts=[]
        for k,label in zip(keys,labels):
            c=comparison[study][k]
            if c['ratio'] is not None and c['ratio']>1:parts.append(f"{label} 高 {(c['ratio']-1)*100:.2f}%（{bnames[baseline.index(c['best_baseline'])]}）")
        text+='- '+name+'：'+('；'.join(parts) if parts else '这四项汇总的实测值均不高于四基线；仍需独立确认及原图专门指标核验')+'。\n'
    text+='\n图见 figures/current_baseline_gaps.pdf、storage_baselines.pdf、workload_baseline_cdfs.pdf。大小区间样本数完整保留；未删除 GUARD 落后的区间或交叉 CDF。数据来源 current_baseline_gaps.json。\n'
    with (ROOT/'REPORT.zh.md').open('a') as f:f.write(text)
    print('Wrote current11-scene/four-baseline development audit and three figures')
if __name__=='__main__':main()
