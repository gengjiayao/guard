#!/usr/bin/env python3
"""Paper-style monochrome plots from the frozen, audited five-seed results."""
import argparse,json
from pathlib import Path
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.font_manager import FontProperties,fontManager
import numpy as np

def main():
    ap=argparse.ArgumentParser();ap.add_argument('analysis',type=Path);ap.add_argument('--font',type=Path,required=True);ap.add_argument('--out',type=Path,required=True)
    a=ap.parse_args();data=json.loads(a.analysis.read_text());a.out.mkdir(parents=True,exist_ok=True)
    fontManager.addfont(str(a.font));family=FontProperties(fname=str(a.font)).get_name()
    plt.rcParams.update({'font.family':family,'font.size':10,'axes.linewidth':.7,'axes.unicode_minus':False,'pdf.fonttype':42,'figure.facecolor':'white'})
    summary={(r['case'],r['arm'],r['metric']):r for r in data['summary']}
    arms=['guard','hpcc','dcqcn','homa'];labels=['GUARD','HPCC','DCQCN','Homa']
    cases=['alltoall256k','alltoall1m','ring16m','concurrent']
    titles=['(a) All-to-All  每对端 256 KiB','(b) All-to-All  每对端 1 MiB','(c) Ring AllReduce  每进程 16 MiB','(d) All-to-All 与 AllReduce 并发']
    fig,axes=plt.subplots(2,2,figsize=(7.2,5.2))
    for ax,c,title in zip(axes.flat,cases,titles):
        metric='makespan_us' if c=='concurrent' else 'mean_cct_us'
        rows=[summary[c,arm,metric] for arm in arms]
        means=np.array([r['mean'] for r in rows])/1000
        errors=np.array([r['ci95_high']-r['mean'] for r in rows])/1000
        bars=ax.bar(range(4),means,width=.6,color=['#282828','#fff','#c9c9c9','#fff'],edgecolor='#222',linewidth=.8,yerr=errors,capsize=3,error_kw={'elinewidth':.8,'capthick':.8},zorder=3)
        for b,h in zip(bars,['','///','','xxx']):b.set_hatch(h)
        ax.set_xticks(range(4));ax.set_xticklabels(labels,fontsize=9)
        ax.set_ylabel('总完工时间 (ms)' if c=='concurrent' else '集合通信完成时间 (ms)',fontsize=10)
        ax.set_title(title,fontsize=10,pad=10)
        ax.grid(axis='y',color='#ddd',linewidth=.5,zorder=0);ax.set_axisbelow(True)
        ax.spines['top'].set_visible(False);ax.spines['right'].set_visible(False)
        ax.set_ylim(0,max(means+errors)*1.23)
        for i,(mean,error) in enumerate(zip(means,errors)):ax.text(i,mean+error+ax.get_ylim()[1]*.025,f'{mean:.2f}',ha='center',va='bottom',fontsize=9)
    fig.subplots_adjust(left=.105,right=.985,bottom=.08,top=.93,hspace=.49,wspace=.29)
    fig.savefig(a.out/'guard_collectives.png',dpi=320);fig.savefig(a.out/'guard_collectives.pdf');plt.close(fig)

if __name__=='__main__':main()
