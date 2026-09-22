"""Plot complete development comparisons, including every adverse metric."""
import json
from pathlib import Path
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

ROOT = Path(__file__).resolve().parents[1]
COLORS = ['#0072B2', '#56B4E9', '#CC79A7', '#882255', '#009E73', '#D55E00', '#E69F00', '#777777']

def main():
    a = json.loads((ROOT/'analysis.json').read_text())
    idx = {(r['study'], r['arm']): r for r in a['runs']}
    def row(arm, study='allreduce_dp2'):
        return idx[study, arm]
    def metric(arm, key, study='allreduce_dp2'):
        return row(arm, study)['metrics'][key]
    def save(fig, name):
        fig.tight_layout()
        for ext in ['png', 'pdf']:
            fig.savefig(ROOT/'figures'/(name+'.'+ext), dpi=160)
        plt.close(fig)
    arms = ['dp2_shared','dp2_startup_peer','dp2_joint8','dp2_joint32','dp2_homa','dp2_hpcc','dp2_dcqcn','dp2_timely']
    labels = ['Shared','Startup','Joint8','Joint32','Homa','HPCC','DCQCN','TIMELY']
    keys = ['fct_mean_us','fct_p99_us','span_ms','queue_worst_port_fixed_mean_us']
    ylabels = ['Mean FCT (ms)','P99 FCT (ms)','Trace span (ms)','Worst-port mean queue (µs)']
    scales = [.001,.001,1,1]
    fig, axes = plt.subplots(2,2,figsize=(12,8))
    for ax, key, ylabel, scale in zip(axes.flat,keys,ylabels,scales):
        vals = [metric(arm,key)*scale for arm in arms]
        ax.bar(labels, vals, color=COLORS)
        ax.set_ylabel(ylabel)
        ax.tick_params(axis='x',rotation=30)
        ax.grid(axis='y',alpha=.2)
        ax.set_ylim(0,max(vals)*1.15)
        for i,v in enumerate(vals):
            ax.text(i,v,f'{v:.2f}',ha='center',va='bottom',fontsize=8)
    fig.suptitle('Full DP2; development seed 301; one observation per profile; lower is better')
    save(fig,'dp2_metrics')
    fig, ax = plt.subplots(figsize=(9,5))
    for arm,label,color in zip(arms,labels,COLORS):
        x = np.sort(np.loadtxt(row(arm)['fct_file'],ndmin=2)[:,6]/1e6)
        assert len(x)==1280
        ax.plot(x,np.arange(1,len(x)+1)/len(x),label=label,color=color)
    ax.set(xlabel='Flow completion time (ms)',ylabel='CDF',title='Full DP2; all 1,280 flows; development seed 301')
    ax.legend(ncol=2,fontsize=9);ax.grid(alpha=.2)
    save(fig,'dp2_cdf')
    ablations=['dp2_shared','dp2_startup_peer','dp2_recovery8','dp2_joint8','dp2_recovery32','dp2_joint32','dp2_joint32_l10']
    abl_labels=['Shared','Startup','Recovery8','Joint8','Recovery32','Joint32','Joint32 λ1']
    fig,axes=plt.subplots(2,2,figsize=(12,8))
    for ax,key,ylabel,scale in zip(axes.flat,keys,ylabels,scales):
        ax.bar(abl_labels,[metric(arm,key)*scale for arm in ablations],color=COLORS[:7])
        ax.set_ylabel(ylabel);ax.tick_params(axis='x',rotation=30);ax.grid(axis='y',alpha=.2)
    fig.suptitle('Matched full-DP2 mechanism controls; development seed 301; lower is better')
    save(fig,'dp2_ablations')
    counter_arms=[r['arm'] for r in a['runs'] if r['study']=='allreduce_dp2' and not r['arm'].endswith('_trace')]
    fig,axes=plt.subplots(2,1,figsize=(13,8),sharex=True)
    for ax,key,label in zip(axes,['pfc_pause_events','timeout_recoveries'],['PFC pause events','Timeout recovery events']):
        vals=[metric(arm,key) for arm in counter_arms]
        ax.bar(range(len(vals)),vals)
        ax.set_ylabel(label);ax.set_yscale('symlog',linthresh=1);ax.grid(axis='y',alpha=.2)
        for i,v in enumerate(vals):ax.annotate(str(v),(i,v),xytext=(0,3),textcoords='offset points',ha='center',fontsize=8)
    counter_names={'dp2_homa':'Homa','dp2_hpcc':'HPCC','dp2_dcqcn':'DCQCN','dp2_timely':'TIMELY'}
    axes[1].set_xticks(range(len(counter_arms)),[counter_names.get(s,s.replace('dp2_','').replace('feedback_','').replace('_',' ')) for s in counter_arms],rotation=40,ha='right')
    fig.suptitle('Full DP2; all unique profiles; development seed 301; zero packet drops in every run')
    save(fig,'dp2_events')
    studies=['ali30','ali50','web40','fb40','alltoall','ring','fairness','fabric','receiver','hybrid']
    names=['Storage30','Storage50','Web','Analytics','All-to-All','Ring','Fairness','Fabric','Receiver','Hybrid']
    regkeys=['fct_mean_us','slowdown_p99','span_ms','queue_worst_port_fixed_mean_us']
    deltas={}
    fig,axes=plt.subplots(2,2,figsize=(14,8))
    for ax,key,ylabel in zip(axes.flat,regkeys,['Mean FCT','P99 slowdown','Trace span','Worst-port mean queue']):
        for j,profile in enumerate(['startup_peer','joint8','joint32']):
            vals=[100*(metric('regression_'+profile,key,s)/metric('regression_shared',key,s)-1) for s in studies]
            for s,v in zip(studies,vals):deltas.setdefault(s,{}).setdefault(profile,{})[key]=v
            ax.bar(np.arange(len(studies))+(j-1)*.25,vals,width=.24,label=profile.replace('_',' '),color=COLORS[j])
        ax.set_xticks(range(len(studies)),names,rotation=40,ha='right')
        ax.set_ylabel(ylabel+' change (%)');ax.axhline(0,color='black',lw=.7);ax.grid(axis='y',alpha=.2)
    axes[0,0].legend(fontsize=8)
    fig.suptitle('Ten original scenes; relative to same-build Shared; positive = worse; development seed 301')
    save(fig,'regression')
    # The topology file defines switch IDs; classification is analysis only.
    topo=Path('/home/gengjiayao/ict/guard-joint/config/leaf_spine_16_100G_OS1.txt').read_text().splitlines()
    switches=set(map(int,topo[1].split()))
    feedback=['feedback_shared_l10','feedback_l10_ack1','feedback_l10_last','feedback_l10_ack1_last']
    feedback_labels=['ACK8, omit last','ACK1, omit last','ACK8, keep last','ACK1, keep last']
    port_metrics={}
    for arm in feedback+['dp2_hpcc']:
        ports=row(arm)['ports']
        classes={'fabric':[p for p in ports if int(p['neighbor_id']) in switches],
                 'receiver':[p for p in ports if int(p['neighbor_id']) not in switches]}
        port_metrics[arm]={}
        for name,ps in classes.items():
            p=max(ps,key=lambda p:p['fixed_average_bytes'])
            port_metrics[arm][name]={'max_mean_us':p['fixed_average_bytes']*8/100000,
                'port':[int(p['node_id']),int(p['if_index']),int(p['neighbor_id'])]}
    fig,axes=plt.subplots(2,2,figsize=(12,8))
    for ax,key,ylabel,scale in zip(axes.flat[:3],keys[:3],ylabels[:3],scales[:3]):
        vals=[metric(arm,key)*scale for arm in feedback]
        ax.bar(feedback_labels,vals,color=COLORS[:4]);ax.set_ylabel(ylabel)
        for i,v in enumerate(vals):ax.text(i,v,f'{v:.2f}',ha='center',va='bottom',fontsize=8)
        ax.set_ylim(0,max(vals)*1.15)
    ax=axes.flat[3]
    for j,cls in enumerate(['fabric','receiver']):
        ax.bar(np.arange(4)+(j-.5)*.35,[port_metrics[arm][cls]['max_mean_us'] for arm in feedback],width=.34,label=cls)
    ax.axhline(metric('dp2_hpcc',keys[3]),color='black',ls=':',label='HPCC: worst port')
    ax.set_xticks(range(4),feedback_labels);ax.set_ylabel('Worst-port mean queue by class (µs)');ax.legend(fontsize=8)
    for ax in axes.flat:ax.tick_params(axis='x',rotation=20);ax.grid(axis='y',alpha=.2)
    fig.suptitle('Fixed λ1; ACK cadence × last-hop feedback; full DP2; development seed 301')
    save(fig,'feedback_factorial')
    (ROOT/'comparison.json').write_text(json.dumps(dict(regression_percent=deltas,feedback_ports=port_metrics),indent=2)+'\n')
    def desc(arm):
        return f"平均 FCT {metric(arm,keys[0])/1000:.3f} ms，P99 {metric(arm,keys[1])/1000:.3f} ms，跨度 {metric(arm,keys[2]):.3f} ms，队列 {metric(arm,keys[3]):.3f} µs。"
    text=f'''# GUARD 启动限速修复与组合控制实验

目标仍在进行中。本轮 {a['attempts']} 次仿真均使用已观察的开发种子 301；没有独立种子确认，没有把候选方案推广到论文。保留所有原始输入、完成记录和不利结果。原图涉及的全部四基线、大小分组、消融、OFLM 和补图仍须在统一方案冻结后完整复测。

## 已定位并修复的问题

此前新增的启动共享机制在同机架长流上留下了过期速率上限。Analytics 的流 4572（11→14，8.496 MB）初始共享速率为 50 Gbps；去掉接收端最后一跳后，ACK 没有网络内部反馈，该初始值一直没有更新。它比关闭启动共享时慢约 651.6 µs，并拖慢竞争流 4260。

源码 guard-joint/5a14a82 为实际降低过启动速率的流记录一次待确认状态。第一次 ACK 没有剩余网络跳数时，恢复网络速率估计到线速，最终发送速率仍受接收端额度约束；第一次 ACK 有网络反馈时清除该状态，后续 ACK 不会重置已经学习的速率。默认未开启的新机制保持关闭。

四组 Analytics 日志均覆盖全部 6,615 条流，无日志行数上限遗漏。修复后流 4572 的完成时间从 5,354.454 µs 降至 4,703.576 µs；关闭启动共享的对照为 4,702.810 µs。修复消除了这次新增回退的主要部分，尚未证明 Analytics 优于全部外部基线。见 figures/startup_diagnosis.pdf。

## DP2 组合方案仍有尾延迟和排队取舍

保留原始 1,280 条流、80 个通信批次、25 MB 消息及固定观察窗口。Shared 是此前开发方案；Startup 增加同接收端启动共享；Joint8/32 再叠加最多 8/32 倍的按反馈间隔恢复增量。全部四个外部基线在同一源码版本重新运行。

'''
    for arm,label in zip(arms,labels):text+=f'- {label}：{desc(arm)}\n'
    text+='\n机制对照也全部保留：\n\n'
    for arm,label in zip(ablations,abl_labels):text+=f'- {label}：{desc(arm)}\n'
    text+='''
Joint32 的 P99 比 Shared 降低，但仍高于 Homa；队列高于 HPCC。不能把这些结果表述为全面领先。图见 figures/dp2_metrics.pdf、dp2_cdf.pdf、dp2_ablations.pdf。CDF 包含所有流，没有截去尾部。Homa 本次测量与较早源码版本略有不同，因此本轮只使用本次同版本基线比较，不把历史数值当作同一次配对测量。

零丢包也不意味着零暂停或零恢复：Joint32 触发 2 次 PFC 暂停（日志开关对照相同），Recovery32 为 24 次，TIMELY 为 3,873 次。Startup、Joint32 λ1、Shared λ1 分别记录 1、16、2 次超时恢复。其余本轮记录中这些计数为零。所有独立 DP2 配置的事件计数见 figures/dp2_events.pdf。

## 十个场景的回归

以下变化相对于同一二进制的 Shared；正值代表退化，不代表相对外部基线。全部四个指标见 figures/regression.pdf。

'''
    for s,name in zip(studies,names):
        for profile in ['startup_peer','joint8','joint32']:
            d=deltas[s][profile]
            text+=f"- {name} / {profile}：平均 FCT {d[regkeys[0]]:+.2f}%，P99 slowdown {d[regkeys[1]]:+.2f}%，跨度 {d[regkeys[2]]:+.2f}%，队列 {d[regkeys[3]]:+.2f}%。\n"
    text+='''
## ACK 频率与最后一跳反馈的完整 2×2 对照

四组均固定 λ=1、关闭启动共享和按间隔恢复，只改变 ACK 每 8/1 包以及是否保留最后一跳 INT。它们用于定位问题；保留最后一跳会改变网络控制与接收控制的分工，不能直接作为只在 DP2 使用的参数修饰。

'''
    for arm,label in zip(feedback,feedback_labels):
        p=port_metrics[arm]
        text+=f"- {label}：{desc(arm)}网络内部最忙端口平均队列 {p['fabric']['max_mean_us']:.3f} µs，接收端最忙端口 {p['receiver']['max_mean_us']:.3f} µs。\n"
    text+='''
见 figures/feedback_factorial.pdf。端口类别仅用于离线分析，控制器没有读取模拟器隐藏的拓扑状态。

ACK8 下保留最后一跳反馈，将接收端最忙端口平均队列从 3.530 降至 0.093 µs，网络内部从 2.401 降至 0.817 µs；残余网络队列仍超过本次 HPCC 的 0.213 µs。ACK1 在两种最后一跳设置下都增加平均 FCT 和跨度，因此更频繁的 ACK 没有解决问题。ACK 流量开销与控制反馈时序的各自贡献尚未隔离；四组 FAST_REACT 均为 0，不能归因于快速反应路径。

## 证据范围和后续工作

- 61 次 = 3 次修复前 Analytics 诊断、2 次修复后 Analytics 日志、12 次完整 DP2、40 次场景回归、4 次反馈因素对照。完整指标在 analysis.json；差值和端口类别在 comparison.json。
- 实际启动路径处理、同目的端启动共享、有界恢复增量和接收端分配器测试均通过。验证脚本核对日志开关配对、输入/二进制/脚本快照、原始归档和完成事件；这是证据完整性验证，不是性能目标通过。
- 随机负载仍使用固定 5 ms 预热，保留全部符合条件的流完成记录；队列分母使用原固定窗口。单个开发种子不生成置信区间，不代替独立确认。
- 下一步根据反馈因素对照处理 DP2 网络内部队列与尾延迟冲突，并继续修复跨场景回退。统一配置通过所有原图及四基线独立复测后，再据此更新论文文字和图片。
'''
    (ROOT/'REPORT.zh.md').write_text(text)
    print('Wrote six comparison figures and complete development report; goal remains active')

if __name__=='__main__':main()
