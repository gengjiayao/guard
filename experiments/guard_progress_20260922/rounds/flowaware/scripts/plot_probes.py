"""Development-only vector plots; distinguish complete traces from diagnostics."""
import json
from pathlib import Path
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import numpy as np

ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'figures';OUT.mkdir(exist_ok=True)
plt.rcParams.update({'font.size':10,'pdf.fonttype':42,'axes.spines.top':False,'axes.spines.right':False})


def save(fig,name):
    fig.tight_layout(rect=(0,0,1,.93))
    for ext in ['pdf','png']:
        fig.savefig(OUT/(name+'.'+ext),dpi=160)
    plt.close(fig)


def main():
    data=json.loads((ROOT/'analysis.json').read_text())
    rows={(r['study'],r['arm']):r for r in data['runs']}
    arms=['reference_reference','order_single_order','shared_full_share128_window1',
          'slots_full_slots4','slots_full_slots8','shared_full_homa','shared_full_hpcc']
    labels=['Previous','Serial','Shared','Shared K=4','Shared K=8','Homa','HPCC']
    colors=['#777777','#CC6677','#0072B2','#56B4E9','#332288','#009E73','#D55E00']
    fig,axs=plt.subplots(2,2,figsize=(11,7))
    for ax,metric,label,scale in zip(axs.flat,
            ['fct_mean_us','fct_p99_us','span_ms','queue_worst_port_fixed_mean_us'],
            ['Mean FCT (ms)','P99 FCT (ms)','Trace span (ms)','Worst-port mean queue (us)'],[.001,.001,1,1]):
        vals=[rows['allreduce_dp2',a]['metrics'][metric]*scale for a in arms]
        ax.bar(range(len(arms)),vals,color=colors)
        ax.set_xticks(range(len(arms)),labels,rotation=30,ha='right')
        ax.set_ylabel(label);ax.grid(axis='y',alpha=.2)
        for i,v in enumerate(vals): ax.annotate(f'{v:.2f}',(i,v),xytext=(0,3),textcoords='offset points',ha='center',fontsize=8)
        ax.margins(y=.15)
    fig.suptitle('Full DP2 trace, development seed 301; one observation per profile')
    save(fig,'dp2_full_metrics')
    fig,ax=plt.subplots(figsize=(8,4.5))
    for a,label,color in zip(arms,labels,colors):
        r=rows['allreduce_dp2',a]
        v=np.sort(np.loadtxt(r['fct_file'],usecols=(6,))/1e6)
        ax.plot(v,np.arange(1,len(v)+1)/len(v),label=label,color=color)
    ax.set_xlabel('Flow completion time (ms)');ax.set_ylabel('CDF');ax.grid(alpha=.2)
    ax.legend(ncol=3,fontsize=9);fig.suptitle('Full DP2 trace, development seed 301; all 1,280 flows')
    save(fig,'dp2_full_cdf')
    arms=['shared_storage_share128_window1','weights_weight0','weights_weight5',
          'weights_weight15','weights_weight20','storage_baselines_homa','storage_baselines_hpcc']
    labels=['Exponent 1','Exponent 0','Exponent 0.5','Exponent 1.5','Exponent 2','Homa','HPCC']
    fig,axs=plt.subplots(1,3,figsize=(12,4.3))
    for ax,metric,label in zip(axs,['fct_mean_us','slowdown_p99','queue_worst_port_fixed_mean_us'],
                              ['Mean FCT (us)','P99 slowdown','Worst-port mean queue (us)']):
        vals=[rows['ali50',a]['metrics'][metric] for a in arms]
        ax.bar(range(len(arms)),vals,color=colors);ax.set_xticks(range(len(arms)),labels,rotation=45,ha='right')
        ax.set_ylabel(label);ax.grid(axis='y',alpha=.2)
    fig.suptitle('Storage 50%, development seed 301; fixed 5 ms warmup')
    save(fig,'storage_weights')
    print('Rendered three development vector figures with adverse outcomes')


if __name__=='__main__':main()
