"""Vector figures from validated new data. Final mode requires all frozen cells."""
import argparse
from collections import defaultdict
import json
from pathlib import Path
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.lines import Line2D

ROOT=Path(__file__).resolve().parents[1]/'holdout'
OUT=ROOT.parent/'figures'/'per_experiment';OUT.mkdir(parents=True,exist_ok=True)
ARMS=['guard','hpcc','homa','dcqcn','timely']
LABELS={'guard':'GUARD','hpcc':'HPCC','homa':'Homa','dcqcn':'DCQCN','timely':'TIMELY'}
SHORT=['G','Hp','Hm','D','T']
COLORS=['#0072B2','#D55E00','#009E73','#CC79A7','#555555']
MARKERS=['o','s','^','D','v'];STYLES=['-','--','-.',':',(0,(4,1,1,1))]
plt.rcParams.update({'font.size':10,'axes.labelsize':10,'axes.titlesize':10,'legend.fontsize':10,'xtick.labelsize':10,'ytick.labelsize':10,'pdf.fonttype':42,'ps.fonttype':42,'font.family':'DejaVu Sans','axes.spines.top':False,'axes.spines.right':False})
data=json.loads((ROOT/'analysis.json').read_text());GROUP=defaultdict(list)
for r in data['runs']:GROUP[r['study'],r['arm']].append(r)
for v in GROUP.values():v.sort(key=lambda r:r['seed'])

def ci(v):
    a=np.array(v,float);m=a.mean()
    return m,2.776445105*np.std(a,ddof=1)/np.sqrt(len(a)) if len(a)>1 else 0
def values(s,a,m):return [r['metrics'][m] for r in GROUP[s,a]]
def finish(fig,name,legend=True):
    if legend:
        handles=[Line2D([0],[0],color=c,marker=m,ls=l,label=LABELS[a],lw=1.6) for a,c,m,l in zip(ARMS,COLORS,MARKERS,STYLES)]
        fig.legend(handles=handles,loc='upper center',ncol=5,frameon=False,bbox_to_anchor=(.5,1.01),handlelength=1.6,columnspacing=1)
        fig.tight_layout(rect=(0,0,1,.92),pad=.6)
    else:fig.tight_layout(pad=.7)
    fig.savefig(OUT/(name+'.pdf'))
    fig.savefig(OUT/(name+'.png'),dpi=150)
    plt.close(fig)
def bars(ax,study,metric,title,scale=1,arms=ARMS,short=SHORT):
    for i,a in enumerate(arms):
        v=values(study,a,metric)
        if not v:continue
        m,e=ci(np.array(v)*scale)
        ax.bar(i,m,yerr=e,color=COLORS[i%5],alpha=.8,edgecolor='black',linewidth=.5,capsize=2,hatch=['','//','..','xx','\\\\'][i%5])
    ax.set_xticks(range(len(arms)),short);ax.set_ylabel(title);ax.grid(axis='y',alpha=.2)

def bins():
    for study in ['ali30','ali50']:
        fig,axs=plt.subplots(2,2,figsize=(7,4.5))
        for ax,q,title in zip(axs.flat,['mean','95','99','99.9'],['Mean','P95','P99','P99.9']):
            for ai,a in enumerate(ARMS):
                rs=GROUP[study,a]
                if not rs:continue
                x=[];y=[];err=[]
                for i in range(8):
                    vals=[r['bins'][i][q] for r in rs if r['bins'][i]['n']>0]
                    if len(vals)!=len(rs):continue
                    m,e=ci(vals);x.append(i);y.append(m);err.append(e)
                ax.errorbar(x,y,yerr=err,color=COLORS[ai],marker=MARKERS[ai],ls=STYLES[ai],lw=1.2,ms=3,capsize=1)
            ax.set_xticks(range(8),['4','8','16','32','64','128','256','2000'],rotation=45)
            ax.set_xlabel('Flow-size bin upper edge (kB)');ax.set_ylabel(title+' slowdown');ax.set_yscale('log');ax.grid(axis='y',alpha=.2)
        finish(fig,study+'_bins')

def overview():
    fig,axs=plt.subplots(1,2,figsize=(7,4.4))
    studies=['ali30','ali50','web40','fb40'];sl=['Storage 30%','Storage 50%','Web search','Analytics']
    for ax,metric,title in zip(axs,['fct_mean_us','slowdown_p99'],['Mean FCT change (%)','P99 slowdown change (%)']):
        for si,s in enumerate(studies):
            g={r['seed']:r for r in GROUP[s,'guard']}
            for ai,a in enumerate(ARMS[1:],1):
                pairs=[100*(g[r['seed']]['metrics'][metric]/r['metrics'][metric]-1) for r in GROUP[s,a] if r['seed'] in g]
                if not pairs:continue
                m,e=ci(pairs);ax.errorbar(m,si*5+ai,xerr=e,color=COLORS[ai],marker=MARKERS[ai],capsize=2)
        ax.axvline(0,color='gray',ls=':',lw=1);ax.set_yticks([i*5+2.5 for i in range(4)],sl);ax.invert_yaxis();ax.set_xlabel(title);ax.grid(axis='x',alpha=.2)
    handles=[Line2D([0],[0],color=COLORS[i],marker=MARKERS[i],ls='none',label='vs. '+LABELS[a]) for i,a in enumerate(ARMS) if i]
    fig.legend(handles=handles,loc='upper center',ncol=4,frameon=False)
    fig.tight_layout(rect=(0,0,1,.9),pad=.7)
    fig.savefig(OUT/'workloads.pdf');fig.savefig(OUT/'workloads.png',dpi=150);plt.close(fig)

def directed():
    fig,axs=plt.subplots(2,3,figsize=(7,4.2))
    for i,s in enumerate(['fabric','receiver2','hybrid']):
        bars(axs[0,i],s,'fct_mean_us','Mean FCT (ms)',.001)
        bars(axs[1,i],s,'queue_worst_port_fixed_mean_us','Worst-port queue (us)')
        axs[0,i].set_title(['Shared fabric','Two-sender fan-in','Mixed bottlenecks'][i])
    finish(fig,'directed')

def oflm():
    fig,axs=plt.subplots(1,3,figsize=(7,2.3))
    for ax,m,y in zip(axs,['fct_mean_us','grants','mean_flow_goodput_gbps'],['Mean FCT (us)','Grant messages (millions)','Mean flow rate (Gb/s)']):
        bars(ax,'ali50',m,y,1e-6 if m=='grants' else 1,arms=['guard','no_selective','no_release','no_oflm'],short=['Full','−S','−R','−Both'])
    finish(fig,'oflm',False)

def fairness():
    fig,axs=plt.subplots(2,3,figsize=(7,4.4))
    jains=[]
    for i,a in enumerate(ARMS):
        ax=axs.flat[i];rs=GROUP['fairness',a]
        if not rs:continue
        r=rs[0];f=next(Path(r['output_dir']).glob('*_flow_bw.txt'));v=np.loadtxt(f,ndmin=2)
        for src in range(4):
            z=v[v[:,1]==src];grid=np.zeros(650)
            idx=np.rint(z[:,0]/100000).astype(int)-1;valid=(idx>=0)&(idx<len(grid))
            grid[idx[valid]]=z[valid,5]
            ax.stairs(grid,np.arange(651)*.1,lw=1,color=COLORS[src],ls=STYLES[src],label='Sender '+str(src))
        ax.set_title(LABELS[a]);ax.set_xlabel('Time (ms)');ax.set_ylabel('Send rate (Gb/s)');ax.set_ylim(0,105);ax.set_xlim(0,65);ax.grid(alpha=.2)
        js=[]
        for rr in rs:
            vv=np.loadtxt(next(Path(rr['output_dir']).glob('*_flow_bw.txt')),ndmin=2)
            # Compare the common 10--12 ms interval, when all four messages remain active.
            means=np.array([vv[(vv[:,1]==s)&(vv[:,0]>1e7)&(vv[:,0]<=1.2e7),5].sum()/20 for s in range(4)])
            js.append(float(means.sum()**2/(4*np.sum(means**2))))
        jains.append((a,js))
    ax=axs.flat[5]
    for i,(a,v) in enumerate(jains):
        m,e=ci(v);ax.errorbar(i,m,yerr=e,color=COLORS[i],marker=MARKERS[i],capsize=2)
    ax.set_xticks(range(5),SHORT);ax.set_ylabel("Jain index, 10–12 ms");ax.set_ylim(0,1.03);ax.grid(axis='y',alpha=.2)
    handles=[Line2D([0],[0],color=COLORS[i],ls=STYLES[i],label='Sender '+str(i)) for i in range(4)]
    fig.legend(handles=handles,loc='upper center',ncol=4,frameon=False)
    fig.tight_layout(rect=(0,0,1,.91),pad=.7);fig.savefig(OUT/'fairness.pdf');fig.savefig(OUT/'fairness.png',dpi=150);plt.close(fig)
    (ROOT/'fairness_metrics.json').write_text(json.dumps({a:{'values':v,'mean':ci(v)[0],'half_width':ci(v)[1]} for a,v in jains},indent=2))

def collectives():
    fig,axs=plt.subplots(2,3,figsize=(7,4.3))
    for row,s in enumerate(['alltoall','allreduce_dp2']):
        bars(axs[row,0],s,'span_ms','Trace span (ms)')
        axs[row,0].set_title('All-to-All' if row==0 else 'DP2 exchange')
        ax=axs[row,1]
        for i,a in enumerate(ARMS):
            rs=GROUP[s,a]
            if not rs:continue
            f=np.loadtxt(rs[0]['fct_file'],ndmin=2)[:,6]/1e6;f.sort()
            ax.plot(f,np.arange(1,len(f)+1)/len(f),color=COLORS[i],ls=STYLES[i],lw=1.4)
        ax.set_xlabel('Flow FCT (ms)');ax.set_ylabel('CDF (seed 501)');ax.set_xscale('log');ax.grid(alpha=.2)
        ax=axs[row,2]
        for i,a in enumerate(ARMS):
            rs=GROUP[s,a]
            if not rs:continue
            series=[sorted([p['fixed_average_bytes']*8/100000 for p in r['ports']],reverse=True)[:3] for r in rs]
            arr=np.array(series);m=arr.mean(axis=0)
            ax.plot([1,2,3],m,color=COLORS[i],marker=MARKERS[i],ls=STYLES[i],lw=1.2,ms=4)
        ax.set_xticks([1,2,3]);ax.set_xlabel('Busiest-port rank');ax.set_ylabel('Mean queue delay (us)');ax.grid(alpha=.2)
    finish(fig,'collectives')

def stress():
    fig,axs=plt.subplots(1,3,figsize=(7,2.4))
    for ax,m,y in zip(axs,['span_ms','drops','timeout_recoveries'],['Trace span (ms)','Dropped packets','Timeout recoveries']):
        bars(ax,'ring',m,y)
        if m!='span_ms':ax.set_yscale('symlog',linthresh=1)
    finish(fig,'ring_stress')

def ring_details():
    fig,axs=plt.subplots(1,2,figsize=(7,2.6))
    bars(axs[0],'ring','fct_mean_us','Mean FCT (ms)',.001)
    bars(axs[1],'ring','queue_worst_port_fixed_mean_us','Worst-port mean queue (us)')
    finish(fig,'ring_latency_queue')

def ablations():
    fig,axs=plt.subplots(1,3,figsize=(7,2.4))
    arms=['guard','keep_last_hop','lambda1','lambda14','receiver_only','receiver_only_legacy'];names=['Full','+LH','λ=1','λ=1.4','R-only','Legacy R']
    for ax,m,y in zip(axs,['fct_mean_us','queue_worst_port_fixed_mean_us','fabric_bindings'],['Mean FCT (ms)','Worst-port queue (us)','Fabric-bound updates']):
        bars(ax,'hybrid',m,y,.001 if m=='fct_mean_us' else 1,arms=arms,short=names)
        ax.tick_params(axis='x',rotation=30)
    finish(fig,'ablations',False)

def receiver_width():
    fig,axs=plt.subplots(2,2,figsize=(7,4))
    for col,study in enumerate(['receiver2','receiver']):
        bars(axs[0,col],study,'fct_mean_us','Mean FCT (ms)',.001)
        bars(axs[1,col],study,'queue_worst_port_fixed_mean_us','Worst-port queue (us)')
        axs[0,col].set_title('Two senders' if col==0 else 'Four senders')
    finish(fig,'receiver_width')

def directed_series():
    fig,axs=plt.subplots(2,3,figsize=(7,4.4))
    arms=ARMS+['receiver_only'];colors=COLORS+['#AA5500'];styles=STYLES+[(0,(2,2))]
    for col,study in enumerate(['fabric_series','receiver2_series','hybrid_series']):
        for i,arm in enumerate(arms):
            rs=GROUP[study,arm]
            if not rs:continue
            r=next(x for x in rs if x['seed']==501)
            bw=np.loadtxt(next(Path(r['output_dir']).glob('*_flow_bw.txt')),ndmin=2)
            flow=bw[bw[:,1]==0]
            grid_rate=np.zeros(60)
            ix=np.rint(flow[:,0]/100000).astype(int)-1;ok=(ix>=0)&(ix<len(grid_rate))
            grid_rate[ix[ok]]=flow[ok,5]
            axs[0,col].stairs(grid_rate,np.arange(61)*.1-1,color=colors[i],ls=styles[i],lw=1)
            q=np.loadtxt(next(Path(r['output_dir']).glob('*_out_qlen.txt')),ndmin=2)
            # Sparse monitor omits zero queues. Reconstruct the max over ports
            # at each 1-us sample before plotting the first 5 ms after injection.
            grid=np.zeros(5001)
            index=np.rint((q[:,0]-2.001e9)/1000).astype(int)
            valid=(index>=0)&(index<len(grid))
            np.maximum.at(grid,index[valid],q[valid,3]*8/100000)
            axs[1,col].plot(np.arange(len(grid))*.001,grid,color=colors[i],ls=styles[i],lw=.8)
        axs[0,col].set_title(['Shared fabric','Two-sender fan-in','Mixed bottlenecks'][col])
        for row in range(2):
            axs[row,col].set_xlim(0,5);axs[row,col].set_xlabel('Time after injection (ms)');axs[row,col].grid(alpha=.2)
        axs[0,col].set_ylabel('Sender 0 rate (Gb/s)');axs[0,col].set_ylim(0,105)
        axs[1,col].set_ylabel('Max-port queue (us)')
    handles=[Line2D([0],[0],color=colors[i],ls=styles[i],label=LABELS.get(a,'Receiver-only')) for i,a in enumerate(arms)]
    fig.legend(handles=handles,loc='upper center',ncol=3,frameon=False)
    fig.tight_layout(rect=(0,0,1,.86),pad=.6)
    fig.savefig(OUT/'directed_series.pdf');fig.savefig(OUT/'directed_series.png',dpi=150);plt.close(fig)

def main():
    p=argparse.ArgumentParser();p.add_argument('--final',action='store_true');a=p.parse_args()
    if a.final:
        expected={t['key'] for name in ['confirmation-manifest.json','series-manifest.json'] for t in json.loads((ROOT/name).read_text())['tasks']}
        got={r['key'] for r in data['runs']}
        assert expected==got,(len(expected),len(got),sorted(expected-got))
        assert not data['failures'],data['failures']
    bins();overview();directed();oflm();fairness();collectives();stress();ring_details();ablations();directed_series();receiver_width()
    print('Rendered vector figures in',OUT)
if __name__=='__main__':main()
