import json
from pathlib import Path
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
ROOT=Path(__file__).resolve().parents[1]
def main():
 a=json.loads((ROOT/'analysis.json').read_text());idx={(r['study'],r['arm']):r for r in a['runs']}
 old=json.loads((ROOT.parent/'guard_rescue_20260921/analysis.json').read_text());oi={(r['study'],r['arm']):r for r in old['runs']}
 before=json.loads((ROOT/'grant_diagnosis.json').read_text());after=json.loads((ROOT/'grant_diagnosis_fixed.json').read_text())
 studies=['ali30','ali50','web40','fb40'];names=['Storage30','Storage50','Web','Analytics'];protocols=['shared_rescue','hpcc','homa','dcqcn','timely'];labels=['GUARD','HPCC','Homa','DCQCN','TIMELY']
 keys=['fct_mean_us','slowdown_p99','queue_worst_port_fixed_mean_us'];titles=['Mean FCT','P99 slowdown','Worst-port mean queue']
 comparison=[]
 for st in studies:
  for p in protocols:
   r=idx[st,'fixed_'+p];b=oi[st,'scenes_shared_rescue' if p=='shared_rescue' else 'baselines_'+p]
   comparison.append(dict(study=st,protocol=p,exact_fct=r['fct_sha256']==b['fct_sha256'],exact_all_metrics=r['metrics']==b['metrics'],before=b['metrics'],after=r['metrics'],relative_change={k:r['metrics'][k]/b['metrics'][k]-1 for k in keys},bins_before=b['bins'],bins_after=r['bins']))
 (ROOT/'identity_comparison.json').write_text(json.dumps(comparison,indent=2)+'\n')
 def save(fig,name):
  fig.tight_layout()
  for ext in ['png','pdf']:fig.savefig(ROOT/'figures'/(name+'.'+ext),dpi=160)
  plt.close(fig)
 fig,axs=plt.subplots(1,3,figsize=(14,5))
 for ax,k,title in zip(axs,keys,titles):
  for i,p in enumerate(protocols):
   vals=[next(v for v in comparison if v['study']==st and v['protocol']==p)['relative_change'][k]*100 for st in studies]
   ax.plot(range(4),vals,marker='o',label=labels[i],alpha=.8)
  ax.axhline(0,color='gray',ls='--');ax.set_xticks(range(4),names,rotation=25);ax.set_title(title);ax.set_ylabel('Change after identity fix (%)');ax.grid(alpha=.2)
 axs[0].legend(fontsize=8);fig.suptitle('Shared 32-bit tag fix; original full workloads, development seed 301');save(fig,'identity_effects')
 cats=['before_first_grant','line_rate','multiple_senders_weighted','multiple_senders_low_cap','single_sender_weighted','single_sender_low_cap']
 cn=['Before first grant','Line-rate cap','Multiple senders, >100 Mb/s','Multiple senders, ≤100 Mb/s','One sender, >100 Mb/s','One sender, ≤100 Mb/s']
 fig,axs=plt.subplots(1,2,figsize=(12,6))
 for ax,st,name in zip(axs,['ali30','ali50'],names):
  bottom=np.zeros(2)
  for cat,label in zip(cats,cn):
   v=np.array([before[st]['duration_fractions'].get(cat,0),after[st]['duration_fractions'].get(cat,0)])*100
   ax.bar([0,1],v,bottom=bottom,label=label);bottom+=v
  ax.set_xticks([0,1],['Before fix','After fix']);ax.set_ylabel('Fraction of total large-flow FCT (%)');ax.set_ylim(0,100);ax.set_title(name);ax.grid(axis='y',alpha=.2)
 fig.legend(*axs[0].get_legend_handles_labels(),loc='lower center',ncol=2,fontsize=9)
 fig.suptitle('Complete grant-cap histories for original eligible flows >256 KB\nCap intervals are not proof that the grant was the active bottleneck')
 fig.tight_layout(rect=(0,.15,1,.92))
 for ext in ['png','pdf']:fig.savefig(ROOT/'figures'/('grant_intervals.'+ext),dpi=160)
 plt.close(fig)
 fig,axs=plt.subplots(2,4,figsize=(16,8))
 for i,st in enumerate(['ali30','ali50']):
  for j,key in enumerate(['mean','95','99','99.9']):
   ax=axs[i,j]
   for p,label in zip(protocols,labels):
    bins=idx[st,'fixed_'+p]['bins'];ax.plot(range(len(bins)),[v[key] if v['n'] else np.nan for v in bins],label=label,marker='o',ms=3)
   ax.set_xticks(range(9),['4K','8K','16K','32K','64K','128K','256K','2M','>2M'],rotation=45);ax.set_yscale('log');ax.set_ylabel('FCT slowdown');ax.set_title(names[i]+' '+('mean' if key=='mean' else 'P'+key));ax.grid(alpha=.2)
 fig.legend(*axs[0,0].get_legend_handles_labels(),loc='upper center',bbox_to_anchor=(.5,.96),ncol=5);fig.suptitle('After shared tag repair: all original size bins and four baselines; development seed 301')
 fig.tight_layout(rect=(0,0,1,.9))
 for ext in ['png','pdf']:fig.savefig(ROOT/'figures'/('storage_fixed_baselines.'+ext),dpi=160)
 plt.close(fig)
 text='# 流编号修复与接收端授权诊断\n\n'
 text+='本轮 44 次原始负载开发实验全部记录，种子均为已经观察过的 301。总体目标仍未完成；本轮没有独立确认，也没有修改论文或 Overleaf。\n\n'
 text+='## 修复的实现错误\n\nFlowIDNUMTag 的编号成员为 32 位，但此前使用 U16 写入和读出，因此编号超过 65535 会回绕。标签声明的序列化长度仍为 8 字节，实际只写入 6 字节。已统一改成 U32 写入和读出，并初始化消息大小字段。真实 Packet 标签往返与拷贝测试在旧构建中复现 65536、65552、131088、2147483647 编号错误，新构建全部通过；标签仍占 8 字节，线上数据包长度不变。修改作用于共享模拟器，因此四个基线一起重测。\n\n'
 text+='## 完整授权历史与核验\n\n'
 for st,name in zip(['ali30','ali50'],names):
  b=before[st];n=after[st]
  text+=f"- {name}：旧/新日志 {b['rows']} / {n['rows']} 行，分别覆盖全部 {b['selected_all_flows']} / {n['selected_all_flows']} 条被大小条件选中的流；原预热规则后 {n['eligible_flows']} 条。无行数上限遗漏，授权发送和接收全部一一匹配。旧接收端编号用低 16 位、源/目的地址及原始大小唯一映射，修复后的编号直接与原始流号一致。\n"
  text+=f"  修复前多发送方低授权（≤100 Mb/s）占合格大消息累计 FCT 的 {b['duration_fractions'].get('multiple_senders_low_cap',0)*100:.2f}%，修复后 {n['duration_fractions'].get('multiple_senders_low_cap',0)*100:.2f}%。这是授权状态区间，不等于实际瓶颈持续时间。\n"
 text+='\n每种负载的日志开/关逐流 FCT 和全部汇总指标一致。旧源无日志结果还与上一轮完全一致。日志过滤仅影响记录，原始流量、完成记录和所有大小区间均保留。原配置的 work_conserving 实际为 0，不能把没有 demand 重分配记录误称为计时器失效。\n\n## 修复后的性能影响\n\n'
 for st,name in zip(studies,names):
  v=next(x for x in comparison if x['study']==st and x['protocol']=='shared_rescue');c=v['relative_change'];text+=f"- {name} GUARD：均值 {c[keys[0]]*100:+.4f}%，P99 slowdown {c[keys[1]]*100:+.4f}%，最忙端口平均队列 {c[keys[2]]*100:+.4f}%；逐流 FCT 完全相同：{v['exact_fct']}。\n"
 text+='\n全部 20 个同协议前后比较、四基线实测值和原大小区间在 identity_comparison.json。图见 figures/identity_effects.pdf、grant_intervals.pdf、storage_fixed_baselines.pdf。\n\n## 仍需处理\n\n这次修复保证接收端排序使用完整编号，不预设它能改善所有性能。Storage 大消息的大部分授权受限区间出现在多发送方竞争时，单发送方限速区间占比很低；此前将共享授权扩展到短消息的方案导致 Ring 丢包，不能重复作为通用修复。下一步应检查多发送方服务宽度与实际可发送需求的匹配，并保留所有原场景回归、完整 DP2、消融及补图的要求。\n'
 (ROOT/'REPORT.zh.md').write_text(text)
 print('Wrote full identity comparison, three figures and report')
if __name__=='__main__':main()
