"""Diagnostic figures, never substitute them for the original evaluation."""
import csv,json,hashlib,re
from collections import Counter,defaultdict,deque
from pathlib import Path
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
ROOT=Path(__file__).resolve().parents[1]
def save(fig,name,rect=None):
 fig.tight_layout(rect=rect)
 for ext in ['png','pdf']:fig.savefig(ROOT/'figures'/(name+'.'+ext),dpi=160)
 plt.close(fig)
def rows(path):return list(csv.DictReader(x for x in path.read_text().splitlines() if not x.startswith('#')))
def main():
 a=json.loads((ROOT/'activity_analysis.json').read_text());b=json.loads((ROOT/'adaptive_activity_analysis.json').read_text())
 fig,axs=plt.subplots(1,2,figsize=(11,4))
 for ax,st in zip(axs,['ali30','ali50']):
  for d,label in [(a,'K1'),(b,'Conditional')]:
   x=np.sort([v['receiver_payload_gbps'] for v in d[st]['intervals'] if v['category']=='high']);ax.plot(x,np.arange(1,len(x)+1)/len(x),label=label)
  ax.set(title={'ali30':'Storage30','ali50':'Storage50'}[st],xlabel='Receiver DATA arrival (Gb/s)',ylabel='Grant-interval CDF',xlim=(0,110));ax.grid(alpha=.2);ax.legend()
 fig.suptitle('High-grant, multi-sender intervals ≥ 1 RTT; overlapping flow intervals, seed 301');save(fig,'arrival_intervals')
 fig,axs=plt.subplots(1,2,figsize=(11,4))
 keys=['pre_sync_ready_fraction','window_bound_fraction','paused_fraction','shorter_ready_other_destination_fraction']
 for ax,st in zip(axs,['ali30','ali50']):
  ax.barh(['Pre-sync ready','Window bound','PFC paused','Shorter other-dest ready'],[100*a[st]['sender'][k] for k in keys]);ax.set(title={'ali30':'Storage30','ali50':'Storage50'}[st],xlabel='Fraction of high-grant receipt observations (%)',xlim=(0,100));ax.grid(axis='x',alpha=.2)
 fig.suptitle('Sender state at grant receipt, before pacing synchronization; seed 301');save(fig,'sender_observations')
 text='# 接收利用率与条件服务宽度诊断\n\n本轮共 65 次完整轨迹测试全部完成：初始诊断与条件并发 30 次，发送端反馈后续对照 35 次。三个独立源码版本：只观测 8f9f6bc；可选条件并发 ef5d5a4；反馈校验 1181dd9。新增策略默认关闭。所有结果来自已观察开发种子 301，不是独立确认，也没有完成“全部图优于全部基线”的目标。\n\n'
 text+='原始输入、指标及所有对照保留。DATA 接收计数覆盖全部流，包括未注册小流；逐宿主字节数与包数守恒。开启观测后完整 FCT 文件与所有指标均保持精确一致。控制器采样完成事件覆盖全部被选流，授权轨迹无上限截断。\n\n'
 for st,name in [('ali30','Storage30'),('ali50','Storage50')]:
  v=a[st]['categories']['high'];text+=f"- {name}：多发送端且授权至少 50 Gb/s 的长授权区间共 {v['interval_count']} 个，聚合 DATA 到达速率中位数 {v['receiver_payload_gbps_quantiles']['50']:.2f} Gb/s；按区间长度加权，低于 50 Gb/s 的比例 {v['interval_duration_weighted_below50_fraction']*100:.2f}%。\n"
 text+='\n上述区间来自不同流，会重叠，不能解读为网络空闲时间比例。收到授权时的状态是同步速率之前的观测，也不是实际 NIC 选中发送的事件。图保留这些口径。\n\n采样器逐窗口验证记录在 width_trace_validation.json：连续窗口使用上一实际采样的 DATA 计数；新测量周期从同一时间戳记录中查找唯一速率相符的起始计数。相同纳秒发生的多个事件可具有不同累计值，不能假设时间戳决定事件顺序。\n\n![](figures/arrival_intervals.png)\n\n![](figures/sender_observations.png)\n'
 (ROOT/'REPORT.zh.md').write_text(text)
if __name__=='__main__':main()
