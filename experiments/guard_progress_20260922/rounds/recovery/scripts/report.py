"""Full development evidence; retain every adverse metric and original scope."""
import json
from pathlib import Path
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
ROOT=Path(__file__).resolve().parents[1]

def main():
 a=json.loads((ROOT/'analysis.json').read_text());index={(r['study'],r['arm']):r for r in a['runs']}
 def row(arm,study='allreduce_dp2'):return index[study,arm]
 def met(arm,key,study='allreduce_dp2'):return row(arm,study)['metrics'][key]
 arms=['dp2_shared','dp2_recovery8','dp2_recovery32','dp2_shared_l10','dp2_recovery8_l10','dp2_homa','dp2_hpcc','dp2_dcqcn','dp2_timely']
 labels=['Shared','Recovery8','Recovery32','Shared λ1','Recovery8 λ1','Homa','HPCC','DCQCN','TIMELY']
 colors=['#0072B2','#56B4E9','#332288','#CC79A7','#882255','#009E73','#D55E00','#E69F00','#777777']
 keys=['fct_mean_us','fct_p99_us','span_ms','queue_worst_port_fixed_mean_us']
 ylabels=['Mean FCT (ms)','P99 FCT (ms)','Trace span (ms)','Worst-port mean queue (µs)'];scales=[.001,.001,1,1]
 fig,axs=plt.subplots(2,2,figsize=(12,7.8))
 for ax,k,yl,scale in zip(axs.flat,keys,ylabels,scales):
  vals=[met(arm,k)*scale for arm in arms];ax.bar(labels,vals,color=colors);ax.set_ylabel(yl);ax.tick_params(axis='x',rotation=35);ax.grid(axis='y',alpha=.2);ax.set_ylim(0,max(vals)*1.15)
  for i,v in enumerate(vals):ax.text(i,v,f'{v:.2f}',ha='center',va='bottom',fontsize=7)
 fig.suptitle('Full DP2; observed development seed301; one observation/profile');fig.tight_layout()
 for ext in ['png','pdf']:fig.savefig(ROOT/'figures'/('dp2_metrics.'+ext),dpi=160)
 plt.close(fig)
 fig,ax=plt.subplots(figsize=(8,4.5))
 for arm,label,c in zip(arms,labels,colors):
  x=np.loadtxt(row(arm)['fct_file'],ndmin=2)[:,6]/1e6;x.sort();ax.plot(x,np.arange(1,len(x)+1)/len(x),label=label,color=c)
 ax.set(xlabel='Flow completion time (ms)',ylabel='CDF',title='Full DP2; all1,280flows; observed seed301');ax.legend(fontsize=7,ncol=3);ax.grid(alpha=.2);fig.tight_layout()
 for ext in ['png','pdf']:fig.savefig(ROOT/'figures'/('dp2_cdf.'+ext),dpi=160)
 plt.close(fig)
 studies=['ali50','web40','fb40','alltoall','ring','fairness'];names=['Storage50%','Web','Analytics','All-to-All','Ring','Fairness']
 regression_keys=['fct_mean_us','slowdown_p99','span_ms','queue_worst_port_fixed_mean_us']
 for phase,profiles,title in [('recovery_cases',['recovery8'],'Bounded recovery'),('peer_cases',['startup_wide','startup_peer'],'Startup sharing scope')]:
  fig,axs=plt.subplots(2,2,figsize=(11,7))
  for ax,k,yl in zip(axs.flat,regression_keys,['Mean FCT','P99 slowdown','Trace span','Worst-port mean queue']):
   for j,profile in enumerate(profiles):
    vals=[(met(phase+'_'+profile,k,s)/met(phase+'_shared',k,s)-1)*100 for s in studies]
    x=np.arange(len(studies))+(j-(len(profiles)-1)/2)*.36
    ax.bar(x,vals,width=.34,label=profile.replace('_',' '))
   ax.set_xticks(range(len(studies)),names,rotation=30);ax.set_ylabel(yl+' change (%)');ax.axhline(0,color='black',lw=.7);ax.grid(axis='y',alpha=.2)
  axs[0,0].legend(fontsize=8);fig.suptitle(title+'; relative to same-build Shared; observed seed301; positive=worse');fig.tight_layout()
  for ext in ['png','pdf']:fig.savefig(ROOT/'figures'/(phase+'.'+ext),dpi=160)
  plt.close(fig)
 def desc(arm):return f"平均 FCT {met(arm,'fct_mean_us')/1000:.3f} ms，P99 {met(arm,'fct_p99_us')/1000:.3f} ms，跨度 {met(arm,'span_ms'):.3f} ms，最忙端口固定窗口平均队列 {met(arm,'queue_worst_port_fixed_mean_us'):.3f} µs，丢包 {met(arm,'drops')}。"
 p99gain=(met('dp2_recovery32','fct_p99_us')/met('dp2_shared','fct_p99_us')-1)*100
 text=f'''# GUARD 反馈恢复与同接收端启动试验

**目标仍未达成，保持进行中。** 本轮 {a['attempts']} 次仿真全部完成：完整 DP2 的恢复机制与四基线对照11次，同接收端启动 DP2 对照2次，六个原始场景的两组回归共30次。均为已观察的开发种子301，没有开启独立确认；没有更换原始流量或删除不利结果，Overleaf未推广这些候选方案。

## 本轮进展与未解决项

- 增加有上限的按反馈间隔折算恢复增量。Recovery32 将完整 DP2 的 P99 相对 Shared 降低 {-p99gain:.2f}%，但平均 FCT 和队列仍有回退，且 P99 仍高于 Homa。不能作为全面领先的统一方案。
- 增加仅在同一接收端的长消息之间共享启动速率的选项。它保留了完整 DP2 的逐流 FCT 和全部汇总指标，并消除了此前额外引入的 Web 回退。Analytics 的启动共享回退仍然存在。
- 两组恢复机制日志开关对照具有逐字节相同的 FCT 文件及相同指标；同接收端与全网卡启动共享的完整 DP2 也逐字节相同。所有结论由验证脚本检查，没有扩大为任意场景都已确定性相同。

## 恢复机制与完整 DP2

原有完整反馈更新使用固定40Mbps增量。本轮只对GUARD完整反馈按距上次完整反馈的时间、原始baseRTT折算增量，并分别设8或32倍的增量上限。小于一个RTT仍用原增量；快速反馈保持原增量。接收端额度、网络拥塞除数、传输窗口和最终速率上下界保留。默认关闭此选项。

'''
 for arm,label in zip(arms,labels):text+=f'- {label}：{desc(arm)}\n'
 text+='''
全部指标和完整CDF见 figures/dp2_metrics.pdf、figures/dp2_cdf.pdf。日志开关的重复曲线不重复绘制，原始记录全部保留。低增益对照保留其延迟代价，不能按不同图切换增益。

## 逐流反馈证据

'''
 for t in json.loads((ROOT/'trace_analysis.json').read_text()):
  text+=f"- {t['arm']}：各自最慢13条流平均低于1Gbps的有效采样点比例 {t['slow13_mean_sample_fraction_low_rate']*100:.2f}%；这些流的采样反馈间隔中位数的中位数 {t['slow13_median_of_flow_median_gaps_us']:.3f} µs。\n"
 text+='''
两组日志均覆盖全部1,280条流和完成事件，无行数上限截断。全部非零的采样恢复增量均匹配实际配置和8320ns原始baseRTT的整数计算。采样比例不是精确时间占比，两组最慢13条流也不保证是相同流。分布图见 figures/feedback_gaps.pdf。

## 跨场景回归

所有百分比均比较同一二进制中的 Shared 对照，正数表示更差；不能解释为对外部基线的独立确认。完整变化图见 figures/recovery_cases.pdf 和 figures/peer_cases.pdf。

'''
 for phase,profile,title in [('recovery_cases','recovery8','Recovery8'),('peer_cases','startup_peer','同接收端启动共享')]:
  text+=f'\n### {title}\n\n'
  for s,n in zip(studies,names):
   r=met(phase+'_'+profile,'fct_mean_us',s)/met(phase+'_shared','fct_mean_us',s)-1
   span=met(phase+'_'+profile,'span_ms',s)/met(phase+'_shared','span_ms',s)-1
   q=met(phase+'_'+profile,'queue_worst_port_fixed_mean_us',s)/met(phase+'_shared','queue_worst_port_fixed_mean_us',s)-1
   text+=f'- {n}：平均 FCT {r*100:+.2f}%，跨度 {span*100:+.2f}%，队列 {q*100:+.2f}%；丢包 {met(phase+"_"+profile,"drops",s)}。\n'
 text+='''
Recovery32 尚未做六场景回归，不能借用 Recovery8 的结果。两项新机制也尚未组合验证。同接收端启动共享只消除了新引入的 Web 回退，没有证明 Web 已优于全部外部基线；存储与 Analytics 原有差距仍在最终目标范围。

## 实现、验证与下一步

- guard-recovery/778d95a：有界的按完整反馈时间恢复，以及实际反馈间隔、增量和已存拥塞状态日志。
- guard-peerstart/7e6a10d：启动共享的同接收端限制；原始全网卡启动方案保留作为消融。
- 实际恢复增量函数10,000随机边界状态、实际接收分配器1,000状态、启动共享的目的端隔离与边界检查通过。
- 每轮保存完整源码提交、二进制/配置/输入哈希及当时的完整分析驱动脚本副本；全部完成记录和原始归档均验证。入口为 analysis.json、trace_analysis.json、validation_checks.json、raw_index.json 和 harness_snapshots/。
- 随机负载沿用固定5ms预热，保留全部合格流的完成记录；队列使用原固定观察窗口。所有图为单个开发种子，未伪造置信区间。

下一步继续处理恢复速度与排队之间的冲突，并定位同接收端启动共享在 Analytics 中回退的原因。需要一套统一配置通过所有原图、消融、大小分组及补图的四基线独立复测后，才能更新论文为优势结论。完整目标保持不变。
'''
 (ROOT/'REPORT.zh.md').write_text(text)
 print('Wrote report and four comparison figures; full goal remains active')
if __name__=='__main__':main()
