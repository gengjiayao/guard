"""Development results with explicit negative outcomes and no confirmation claims."""
import json
from pathlib import Path
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
ROOT=Path(__file__).resolve().parents[1]

def main():
 data=json.loads((ROOT/'analysis.json').read_text()); rows={r['arm']:r for r in data['runs'] if r['study']=='allreduce_dp2'}
 arms=['stable_share128_window1','stable_startup','target_shared_alladapt','target_startup_alladapt','stable_homa','stable_hpcc','stable_dcqcn','stable_timely']
 names=['Shared','Startup share','Adaptive target','Both','Homa','HPCC','DCQCN','TIMELY']
 colors=['#0072B2','#56B4E9','#CC79A7','#332288','#009E73','#D55E00','#E69F00','#777777']
 fig,axs=plt.subplots(2,2,figsize=(11,7))
 for ax,key,label,scale in zip(axs.flat,['fct_mean_us','fct_p99_us','span_ms','queue_worst_port_fixed_mean_us'],['Mean FCT (ms)','P99 FCT (ms)','Trace span (ms)','Worst-port mean queue (µs)'],[.001,.001,1,1]):
  vals=[rows[a]['metrics'][key]*scale for a in arms]
  ax.bar(names,vals,color=colors);ax.tick_params(axis='x',rotation=35);ax.set_ylabel(label);ax.grid(axis='y',alpha=.2)
  for i,v in enumerate(vals):ax.text(i,v,f'{v:.2f}',ha='center',va='bottom',fontsize=7)
  ax.set_ylim(0,max(vals)*1.15)
 fig.suptitle('Full DP2; development seed 301, one observation per profile');fig.tight_layout();fig.savefig(ROOT/'figures/stable_metrics.png',dpi=160);fig.savefig(ROOT/'figures/stable_metrics.pdf');plt.close(fig)
 fig,ax=plt.subplots(figsize=(8,4.5))
 for a,n,c in zip(arms,names,colors):
  x=np.loadtxt(rows[a]['fct_file'],ndmin=2)[:,6]/1e6;x.sort();ax.plot(x,np.arange(1,len(x)+1)/len(x),label=n,color=c)
 ax.set(xlabel='Flow completion time (ms)',ylabel='CDF',title='Full DP2; all 1,280 flows, development seed 301');ax.legend(fontsize=8,ncol=2);ax.grid(alpha=.2);fig.tight_layout();fig.savefig(ROOT/'figures/stable_cdf.png',dpi=160);fig.savefig(ROOT/'figures/stable_cdf.pdf');plt.close(fig)
 def m(arm,key):return rows[arm]['metrics'][key]
 def desc(arm):return f"平均 FCT {m(arm,'fct_mean_us')/1000:.3f} ms，P99 {m(arm,'fct_p99_us')/1000:.3f} ms，跨度 {m(arm,'span_ms'):.3f} ms，最忙端口固定窗口平均队列 {m(arm,'queue_worst_port_fixed_mean_us'):.3f} µs，丢包 {m(arm,'drops')}。"
 text='''# GUARD 慢流定位与初始速率试验

**目标仍未达成，保持进行中。** 本轮完成 ATTEMPTS 次原始轨迹开发仿真，全部为已观察的种子 301；没有开启新种子的独立确认。DP2 保留原始 1,280 条流，不用短前缀替代。Overleaf 未更新为全面领先。

## 已定位的问题

最慢的 13 条流（约 1%）平均每条流约 74% 的有效采样点低于 1 Gbps，而接收授权一直为 100 Gbps；其窗口几乎没有占满。关闭网络控制后，长尾明显缩短，但队列显著增大。轮转发送仍存在长尾。证据支持网络反馈长期限速是主要瓶颈；不能把稀疏采样的比例解释为精确时间占比。

关闭网络控制：NOFABRIC

轮转发送：RR

## 可重复性修复

原版本接收端从指针哈希容器遍历并立即发出授权，日志内存分配能改变授权顺序。同一二进制开关日志时，原始 DP2 平均 FCT 存在约 1.5% 的差异。现将传统授权的发送顺序固定为 flow ID。

修复后在共享额度和初始速率共享两个配置中，开关日志的完整 1,280 条 FCT 文件 SHA-256 相同，全部汇总性能指标相同。此项结论由 validation_checks.json 验证；没有扩展为所有可选分配器和场景已完全消除非确定性。

## 新方案及完整 DP2 对照

初始速率共享仅对超过 128 BDP 的新消息启用，根据本机仍有待发字节的长消息数量分配初始速率，随后保留原反馈控制。另测试既有队列自适应目标覆盖长消息，分别单独启用与组合启用。

'''.replace('ATTEMPTS',str(data['attempts'])).replace('NOFABRIC',desc('causal_shared_nofabric_trace')).replace('RR',desc('scheduler_shared_rr_trace'))
 for a,n in zip(arms,names):text+=f'- {n}：{desc(a)}\n'
 text+='''
对照全部保留在 figures/stable_metrics.pdf 和 figures/stable_cdf.pdf；CDF 中的交叉与不利长尾未被删除。

## 跨场景回归

以下比较使用相同新二进制，区别仅在是否启用初始速率共享。

'''
 for study in ['ali50','web40','fb40','alltoall','ring','fairness']:
  group={r['arm']:r for r in data['runs'] if r['study']==study};base=group['regressions_share128_window1'];new=group['regressions_startup']
  change=(new['metrics']['fct_mean_us']/base['metrics']['fct_mean_us']-1)*100
  span=(new['metrics']['span_ms']/base['metrics']['span_ms']-1)*100
  text+=f"- {study}：平均 FCT {change:+.2f}%，跨度 {span:+.2f}%；丢包 {new['metrics']['drops']}。\n"
 text+='''
Web 的回退意味着初始速率共享不能直接作为统一方案采用。所有其他原图、存储大小分组、消融、公平性曲线、补图和四基线仍在最终验收范围内；本轮没有用 DP2 对照替代全范围确认。

## 证据与限制

- 源码 guard-tailtrace/bab0719 增加有界的按流事件采样；guard-startupshare/06a7ec7 增加初始速率共享，992cc57 固定传统授权发送顺序。新性能功能默认关闭。
- 实际分配器 1,000 状态检查及初始速率边界检查通过。原源码工作区未替换，候选方案未推广。
- 全部完成身份、输入/配置/二进制、原始归档哈希核验见 analysis.json、各轮 manifest、raw_index.json、validation_checks.json。
- trace_analysis.json 包含逐流诊断，所有追踪运行均保留全部 1,280 个完成事件，没有因行数上限丢失事件；标记 sampled_out 的事件是预定时间间隔采样跳过，不能当成完整包级轨迹。
- 同一 ACK 回调在记录 complete 后还可能记录同一时间戳的 hpcc 事件；分析按 complete 事件匹配真实 FCT，并检查后续事件没有推进模拟时间。
- 随机负载沿用固定 5 ms 预热，保留全部合格流的完成记录。队列为原始固定观察窗口；所有本轮数字属于开发数据，不提供多种子置信区间。

下一步依据完整 DP2 的反馈和跨场景回退，继续修改拥塞控制的恢复机制；保留接收授权约束，不能用简单关闭网络反馈来换取长尾优势。所有原图优于四基线或部分改善其余持平的目标保持不变。
'''
 (ROOT/'REPORT.zh.md').write_text(text)
 print('Wrote report and full four-baseline DP2 figures; goal remains active')
if __name__=='__main__':main()
