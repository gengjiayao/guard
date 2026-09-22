"""Measured batch-service and representation-order effects; preserve all outcomes."""
import json
from pathlib import Path
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
ROOT=Path(__file__).resolve().parents[1]
KEYS=['fct_mean_us','fct_p99_us','span_ms','queue_worst_port_fixed_mean_us']
LABELS=['Mean FCT (ms)','P99 FCT (ms)','Trace span (ms)','Worst-port mean queue (µs)']
SCALES=[.001,.001,1,1]

def main():
    a=json.loads((ROOT/'analysis.json').read_text())
    idx={(r['study'],r['arm']):r for r in a['runs']}
    def row(arm,study='allreduce_dp2'):return idx[study,arm]
    def m(arm,k,study='allreduce_dp2'):return row(arm,study)['metrics'][k]
    def save(fig,name):
        fig.tight_layout()
        for ext in ['pdf','png']:fig.savefig(ROOT/'figures'/(name+'.'+ext),dpi=160)
        plt.close(fig)
    def bars(arms,names,title,name):
        fig,axs=plt.subplots(2,2,figsize=(13,8))
        for ax,k,label,scale in zip(axs.flat,KEYS,LABELS,SCALES):
            vals=[m(arm,k)*scale for arm in arms]
            ax.bar(np.arange(len(arms)),vals,color=plt.get_cmap('tab10')(np.arange(len(arms))%10))
            ax.set_xticks(range(len(arms)),names,rotation=35,ha='right')
            ax.set_ylabel(label);ax.grid(axis='y',alpha=.2);ax.set_ylim(0,max(vals)*1.16)
            for i,v in enumerate(vals):ax.annotate(f'{v:.2f}',(i,v),xytext=(0,3),textcoords='offset points',ha='center',fontsize=8)
        fig.suptitle(title+'\nFull DP2; development seed 301; lower is better');save(fig,name)
    order_arms=['homa_order_homa_'+mode+'_'+suffix for mode in ['legacy','stable'] for suffix in ['a','b','small','large']]
    order_names=[mode+' '+suffix for mode in ['Legacy','Stable'] for suffix in ['default A','default B','11 buckets','257 buckets']]
    bars(order_arms,order_names,'Homa: only internal RESEND scan representation changes','homa_order')
    profiles=['shared_cursor','shared_batch','joint32_cursor','joint32_batch','shared_l10_cursor','shared_l10_batch']
    names=['Shared cursor','Shared batch','Joint32 cursor','Joint32 batch','Shared λ1 cursor','Shared λ1 batch']
    arms=['batch_dp2_'+p for p in profiles]
    bars(arms,names,'GUARD: three paired ACK-batch service controls','batch_controls')
    bprofiles=profiles[:4]+['homa','hpcc','dcqcn','timely']
    bnames=names[:4]+['Homa','HPCC','DCQCN','TIMELY']
    barms=['batch_dp2_'+p for p in bprofiles]
    bars(barms,bnames,'Same-build comparison with all four baselines','batch_baselines')
    fig,ax=plt.subplots(figsize=(10,6))
    for arm,name in zip(barms,bnames):
        x=np.sort(np.loadtxt(row(arm)['fct_file'],ndmin=2)[:,6]/1e6)
        ax.plot(x,np.arange(1,len(x)+1)/len(x),label=name)
    ax.set(xlabel='Flow completion time (ms)',ylabel='CDF',title='Full original DP2: all 1,280 flows; development seed 301')
    ax.legend(fontsize=9,ncol=2);ax.grid(alpha=.2);save(fig,'batch_cdf')
    fig,axs=plt.subplots(1,3,figsize=(15,5))
    for rank,ax in enumerate(axs):
        vals=[sorted((p['fixed_average_bytes']*8/100000 for p in row(arm)['ports']),reverse=True)[rank] for arm in barms]
        ax.bar(range(len(barms)),vals);ax.set_xticks(range(len(barms)),bnames,rotation=45,ha='right')
        ax.set_ylabel('Fixed-window mean queue (µs)');ax.set_title(f'Busiest port rank {rank+1}')
        ax.set_yscale('log');ax.grid(axis='y',alpha=.2)
    fig.suptitle('Full DP2: original three queue ranks retained; lower is better');save(fig,'queue_ranks')
    fig,axs=plt.subplots(3,1,figsize=(13,11),sharex=True)
    event_arms=arms+barms[4:];event_names=names+bnames[4:]
    for ax,key,label in zip(axs[:2],['timeout_recoveries','pfc_pause_events'],['Generic RTO recovery events','PFC pause events']):
        vals=[m(arm,key) for arm in event_arms]
        ax.bar(range(len(vals)),vals);ax.set_ylabel(label);ax.set_yscale('symlog',linthresh=1);ax.grid(axis='y',alpha=.2)
        for i,v in enumerate(vals):ax.annotate(str(v),(i,v),xytext=(0,3),textcoords='offset points',ha='center',fontsize=8)
    native=[row(arm)['stats'].get('homa_resends_sent',0) for arm in event_arms]
    axs[2].bar(range(len(native)),native);axs[2].set_ylabel('Homa native RESENDs');axs[2].grid(axis='y',alpha=.2)
    axs[2].set_ylim(0,max(native)*1.18)
    for i,(arm,v) in enumerate(zip(event_arms,native)):
        label=str(v) if arm.endswith('_homa') else 'n/a'
        axs[2].annotate(label,(i,v),xytext=(0,3),textcoords='offset points',ha='center',fontsize=8)
    axs[-1].set_xticks(range(len(event_arms)),event_names,rotation=40,ha='right')
    fig.suptitle('Full DP2: recovery and pause counts; development seed 301');save(fig,'batch_events')
    studies=['web40','fb40','alltoall','ring','ali30','ali50']
    snames=['Web','Analytics','All-to-All','Ring','Storage30','Storage50']
    rkeys=['fct_mean_us','slowdown_p99','span_ms','queue_worst_port_fixed_mean_us']
    changes={};fig,axs=plt.subplots(2,2,figsize=(13,8))
    for ax,key,label in zip(axs.flat,rkeys,['Mean FCT','P99 slowdown','Trace span','Worst-port mean queue']):
        for j,parent in enumerate(['shared','joint32']):
            xs=[];vals=[]
            for i,study in enumerate(studies):
                if parent=='joint32' and i>=4:continue
                phase='batch_cases' if i<4 else 'storage'
                v=100*(m(phase+'_'+parent+'_batch',key,study)/m(phase+'_'+parent+'_cursor',key,study)-1)
                xs.append(i+(j-.5)*.35);vals.append(v)
                changes.setdefault(study,{}).setdefault(parent,{})[key]=v
            ax.bar(xs,vals,width=.34,label=parent)
        ax.set_xticks(range(6),snames,rotation=30,ha='right');ax.set_ylabel(label+' change (%)')
        ax.axhline(0,color='black',lw=.7);ax.grid(axis='y',alpha=.2)
    axs[0,0].legend();fig.suptitle('ACK-batch service versus matched cursor; positive = worse\nJoint32 Storage not measured in this round');save(fig,'batch_regression')
    fig,axs=plt.subplots(2,4,figsize=(16,8))
    for i,study in enumerate(['ali30','ali50']):
        for j,k in enumerate(['mean','95','99','99.9']):
            ax=axs[i,j]
            for suffix in ['cursor','batch']:
                bins=row('storage_shared_'+suffix,study)['bins']
                ax.plot(range(len(bins)),[b[k] if b['n'] else np.nan for b in bins],marker='o',label=suffix)
            ax.set_xticks(range(len(bins)),['4K','8K','16K','32K','64K','128K','256K','2M','>2M'],rotation=45)
            ax.set_yscale('log');ax.set_title(snames[4+i]+' '+('mean' if k=='mean' else 'P'+k))
            ax.set_ylabel('FCT slowdown');ax.grid(alpha=.2)
    axs[0,0].legend();fig.suptitle('Storage: every original size bin retained (upper bounds in bytes)\nDevelopment seed 301; full bin counts retained in analysis.json');save(fig,'storage_bins')
    dpchanges={p:{k:100*(m('batch_dp2_'+p+'_batch',k)/m('batch_dp2_'+p+'_cursor',k)-1) for k in KEYS} for p in ['shared','joint32','shared_l10']}
    (ROOT/'comparison.json').write_text(json.dumps(dict(regression_percent=changes,dp2_percent=dpchanges),indent=2)+'\n')
    def desc(arm):
        return f"平均 FCT {m(arm,KEYS[0])/1000:.3f} ms，P99 {m(arm,KEYS[1])/1000:.3f} ms，跨度 {m(arm,KEYS[2]):.3f} ms，队列 {m(arm,KEYS[3]):.3f} µs，超时恢复 {m(arm,'timeout_recoveries')}，PFC 暂停 {m(arm,'pfc_pause_events')}。"
    text=f'''# GUARD ACK 批次调度与 Homa 重复性

完整论文优势目标仍在进行中。本轮共 {a['attempts']} 次仿真尝试，{a['completed']} 次完成，{len(a['failures'])} 次失败。所有运行使用已经观察的开发种子 301；原始输入、预热、全部流和固定队列观察窗口保留。本轮没有进行新种子的独立确认，也没有将候选修改推广到论文。

## Homa 重发顺序

Homa 原先按指针哈希表的迭代顺序发送同时到期的 RESEND。仅改变哈希桶的内部表示，旧实现的完整 DP2 就产生三组不同 FCT；这不是协议参数变化。修复按消息 ID 和端点的固定顺序发送同一批到期重发，保持原定时器、重发范围、授权及优先级规则。

同一二进制的两次默认桶重复以及 11/257 桶两组检查，修复后的逐流 FCT 和全部汇总指标完全相同。另一个包含 GUARD 调度改动的构建也运行 Homa，用于检查跨构建一致性。全部旧结果仍在记录中，没有根据性能挑选桶或顺序。固定顺序的意义是消除容器表示对结果的影响，不能证明该仿真完整等同于其他 Homa 实现。

图见 figures/homa_order.pdf，精确一致性检查见 validation_checks.json。

## GUARD 调度修改

已有独立公平轮询每次服务一个包，可能让低优先级流长期停在不足八个包的 ACK 批次中。新选项保持原有最短流量子和一次公平发送的份额，在连续公平机会中优先补齐同一流当前批次。目标使用发送端累计确认序列加既有 ACK 间隔，开始后固定；补齐、流结束、索引身份变化或失去发送资格后，继续轮询其他流。

该修改默认关闭，要求开启独立公平游标，没有添加 ACK 定时器或修改 RTO。实际调度器测试验证配置的 64:1 份额、部分批次补齐、三名竞争者都得到服务，以及暂停、窗口、发送时间、完成、索引复用时不阻塞其他合格流。单元测试不替代下列完整性能测量。

## 完整 DP2

每次运行均为原始 1,280 条流、每主机 2 GB 的完整轨迹。三个父配置各做同构建配对，四个外部基线使用相同构建及输入。

'''
    for arm,name in zip(event_arms,event_names):text+=f'- {name}：{desc(arm)}\n'
    text+='\n图见 figures/batch_controls.pdf、batch_baselines.pdf、batch_cdf.pdf、queue_ranks.pdf、batch_events.pdf。Homa 的通用 RTO 计数为零，但发生 10,618 次原生 RESEND，两类计数在图中分别呈现。CDF 和三个最繁忙端口的队列同时保留；均值改善不能覆盖尾延迟或队列退化。\n\n## 跨场景回归\n\n'
    for study,name in zip(studies,snames):
        for parent,d in changes[study].items():
            text+=f"- {name} / {parent}：平均 FCT {d[rkeys[0]]:+.2f}%，P99 slowdown {d[rkeys[1]]:+.2f}%，跨度 {d[rkeys[2]]:+.2f}%，队列 {d[rkeys[3]]:+.2f}%。\n"
    text+='''
图见 figures/batch_regression.pdf 和 storage_bins.pdf。Storage 每个大小区间的样本数、均值及 P95/P99/P99.9 均保留在 analysis.json。所有百分比都是开发样本的实测变化，微小差别尚不能称为统计持平。

## 范围与证据

原论文所有负载、大小分组、网络/接收/混合拥塞、严格消融、OFLM、公平性、All-to-All、完整 DP2、Ring 及两组补图继续保留在验收范围。本轮覆盖六个跨场景配对和完整 DP2，并非全部原图的四基线确认。当前还没有一套统一配置在全部指标上达到用户要求。

每轮保存源码提交、二进制、拓扑、输入与驱动脚本哈希；原始输出归档见 raw_index.json。analysis.json、comparison.json、validation_checks.json 提供可复查数值及完整性验证。控制日志配对检查逐流 FCT 和全部指标一致，并逐项检查完成事件与截断数。源码隔离在 guard-homastable、guard-ackbatch 和 guard-servicebudget，原 guard 源码及用户数据保留。
'''
    (ROOT/'REPORT.zh.md').write_text(text)
    print('Wrote eight figures and complete development report')
if __name__=='__main__':main()
