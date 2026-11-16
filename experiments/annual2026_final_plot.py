#!/usr/bin/env python3
"""Monochrome scientific figure from audited overall-P99 results."""
import argparse,json
from pathlib import Path
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.font_manager import fontManager,FontProperties
import numpy as np

def main():
    p=argparse.ArgumentParser();p.add_argument('analysis',type=Path);p.add_argument('--out',type=Path,required=True);p.add_argument('--font',type=Path,required=True);a=p.parse_args()
    d=json.loads(a.analysis.read_text());a.out.mkdir(parents=True,exist_ok=True)
    fontManager.addfont(str(a.font));family=FontProperties(fname=str(a.font)).get_name()
    plt.rcParams.update({'font.family':family,'font.size':9,'axes.linewidth':.7,'axes.unicode_minus':False,'pdf.fonttype':42,'figure.facecolor':'white'})
    s={(r['case'],r['group'],r['metric'],r['arm']):r for r in d['summary']}
    e={(r['case'],r['group'],r['metric'],r['baseline']):r for r in d['effects']}
    arms=['guard','hpcc','dcqcn','homa'];labels=['GUARD','HPCC','DCQCN','Homa']
    fig,axs=plt.subplots(2,2,figsize=(7.2,5.2))
    for ax,load,letter in zip(axs.flat,[50,70,80],['a','b','c']):
        case=f'AliStorage2019-L{load}';rows=[s[case,'all','p99_fct_us',arm] for arm in arms]
        high=max(r['ci95_high'] for r in rows);low=min(r['ci95_low'] for r in rows)
        for i,(r,marker,fc) in enumerate(zip(rows,['D','o','^','s'],['#202020','white','#999999','white'])):
            ax.errorbar(i,r['mean'],yerr=[[r['mean']-r['ci95_low']],[r['ci95_high']-r['mean']]],fmt=marker,ms=5.5,mfc=fc,mec='black',color='black',capsize=3,elinewidth=.8,capthick=.8,zorder=3)
            ax.text(i,r['ci95_high']*1.13,f'{r["mean"]:,.1f}',ha='center',va='bottom',fontsize=8)
        ax.set_yscale('log');ax.set_ylim(max(1,low*.65),high*1.8)
        ax.set_xlim(-.5,3.5);ax.set_xticks(range(4));ax.set_xticklabels(labels,fontsize=9)
        ax.set_ylabel('整体 P99 FCT (μs，对数刻度)',fontsize=9)
        ax.set_title(f'({letter}) 主机负载 {load}%   {rows[0]["n_seeds"]} 个种子',fontsize=10,pad=9)
        effect=e[case,'all','p99_fct_us','homa']
        ax.text(.03,.04,f'相对 Homa 下降 {effect["mean"]:.2f}%',transform=ax.transAxes,fontsize=9)
        ax.grid(axis='y',which='major',color='#d7d7d7',lw=.5);ax.set_axisbelow(True)
        ax.spines['top'].set_visible(False);ax.spines['right'].set_visible(False)
    ax=axs.flat[3];effect=e['AliStorage2019-L80','all','p99_fct_us','homa']
    values=effect['reductions_percent'];x=np.arange(len(values))
    ax.bar(x,values,color='#bbbbbb',edgecolor='#222222',linewidth=.65,width=.65,zorder=3)
    ax.axhline(10,color='#555555',ls='--',lw=.8,label='10% 参考线',zorder=4)
    ax.axhline(effect['mean'],color='#111111',lw=1,label=f'均值 {effect["mean"]:.2f}%',zorder=4)
    ax.set_ylim(min(0,min(values)-3),max(30,max(values)+7));ax.set_ylabel('整体 P99 降幅 (%)')
    ax.set_xticks(x);ax.set_xticklabels(effect['seeds'],rotation=45,ha='right',fontsize=8)
    ax.set_title('(d) 80%负载下逐种子与 Homa 配对比较',fontsize=10,pad=9)
    for i,v in enumerate(values):ax.text(i,v+.5,f'{v:.1f}',ha='center',va='bottom',fontsize=7.5)
    ax.legend(loc='upper right',frameon=False,fontsize=8,ncol=2,handlelength=1.5,columnspacing=.7)
    ax.spines['top'].set_visible(False);ax.spines['right'].set_visible(False)
    ax.grid(axis='y',color='#d7d7d7',lw=.5);ax.set_axisbelow(True)
    fig.subplots_adjust(left=.105,right=.985,bottom=.10,top=.94,wspace=.33,hspace=.43)
    fig.savefig(a.out/'guard_overall_p99.png',dpi=320);fig.savefig(a.out/'guard_overall_p99.pdf');plt.close(fig)

if __name__=='__main__':main()
