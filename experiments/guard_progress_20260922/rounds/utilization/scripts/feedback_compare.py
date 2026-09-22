import json
from pathlib import Path
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from report import ROOT,save

def main():
 a=json.loads((ROOT/'analysis.json').read_text());idx={(r['study'],r['arm']):r for r in a['runs']}
 studies=['ali30','ali50','web40','fb40','fabric','receiver','hybrid','fairness','alltoall','ring','allreduce_dp2'];names=['Storage30','Storage50','Web','Analytics','Fabric','Receiver','Hybrid','Fairness','All-to-All','Ring','DP2'];profiles=['shared_rescue','feedback_only','feedback_width'];labels=['K1','Feedback only','Feedback + widening'];out={};fair={}
 keys=['fct_mean_us','slowdown_p99','span_ms','queue_worst_port_fixed_mean_us'];titles=['Mean FCT','P99 slowdown','Trace span','Worst-port mean queue']
 for st in studies:
  b=idx[st,'feedback_shared_rescue'];parent=idx[st,'width_shared_rescue'];assert b['fct_sha256']==parent['fct_sha256'] and b['metrics']==parent['metrics']
  out[st]={}
  for profile,label in zip(profiles,labels):
   r=idx[st,'feedback_'+profile];out[st][label]=dict(metrics=r['metrics'],ratios={k:r['metrics'][k]/b['metrics'][k] for k in keys},exact_fct_vs_k1=r['fct_sha256']==b['fct_sha256'],exact_metrics_vs_k1=r['metrics']==b['metrics'],cap_report_packets=r['stats']['guard_cap_reports_sent'],cap_report_bytes=r['stats']['guard_cap_report_bytes_sent'],cap_report_received=r['stats']['guard_cap_reports_received'],bins=r['bins'])
   if st=='fairness':
    f=np.loadtxt(r['fct_file'],ndmin=2);assert np.all(f[:,5]<=2010000000) and np.all(f[:,5]+f[:,6]>2012000000);v=np.loadtxt(next(Path(r['output_dir']).glob('*_flow_bw.txt')),ndmin=2);rates=[]
    for src in range(4):
     z=v[v[:,1]==src];grid=np.zeros(650);ids=np.rint(z[:,0]/100000).astype(int)-1;ok=(ids>=0)&(ids<650);assert len(set(ids[ok]))==sum(ok);grid[ids[ok]]=z[ok,5];rates.append(float(grid[100:120].mean()))
    fair[label]=dict(rates=rates,jain=sum(rates)**2/(4*sum(x*x for x in rates)))
   if st=='allreduce_dp2':assert len(np.loadtxt(r['fct_file']))==1280
 result=dict(studies=out,fairness=fair,all_cross_source_k1_exact=True,independent_confirmation=False)
 (ROOT/'feedback_comparison.json').write_text(json.dumps(result,indent=2)+'\n')
 fig,axs=plt.subplots(1,4,figsize=(16,7),sharey=True)
 for ax,k,title in zip(axs,keys,titles):
  values=[]
  for off,label,marker,color in [(-.11,'Feedback only','x','#777777'),(.11,'Feedback + widening','o','#2878a0')]:
   vals=[out[st][label]['ratios'][k] for st in studies];values+=vals;ax.scatter(vals,np.arange(11)+off,label=label,marker=marker,color=color)
   if off>0:
    for i,v in enumerate(vals):ax.annotate(f'{(v-1)*100:+.2f}%',(v,i+off),xytext=(5,0),textcoords='offset points',fontsize=7,va='center')
  ax.axvline(1,ls='--',color='gray');lo,hi=min(values+[1]),max(values+[1]);span=max(hi-lo,.1);ax.set_xlim(lo-span*.12,hi+span*.4);ax.set(title=title,xlabel='Measured result / K1');ax.grid(alpha=.2)
 axs[0].set_yticks(range(11),names);axs[0].invert_yaxis();handles,legend_labels=axs[1].get_legend_handles_labels();fig.legend(handles,legend_labels,loc='upper center',bbox_to_anchor=(.5,.965),ncol=2,fontsize=9);fig.suptitle('Fresh sender feedback before widening: all eleven original scenes, seed 301');save(fig,'feedback_changes',rect=(0,0,1,.94))
 fig,ax=plt.subplots(figsize=(10,5));x=np.arange(11)
 for off,label in [(-.18,'Feedback only'),(.18,'Feedback + widening')]:ax.bar(x+off,[out[st][label]['cap_report_bytes']/1000 for st in studies],width=.36,label=label)
 ax.set(xticks=x,xticklabels=names,ylabel='Actual CAP_REPORT traffic (kB)',title='Additional control traffic travels through simulated links and queues');ax.tick_params(axis='x',rotation=30);ax.legend();ax.grid(axis='y',alpha=.2);save(fig,'feedback_cost')
 text='\n## 发送端反馈校验后的实测\n\n在独立源码 1181dd9 上追加 33 次完整原场景对照，以及 Storage50/Hybrid 两次无行为影响的观测重跑。共 65 次。反馈必须经过真实链路传输，并带当前高授权轮次的标识；发送端要求高授权激活一 RTT 后的新完整反馈，接收端要求报告不超过两 RTT。另设只发反馈、不扩并发的对照，以区分控制报文和策略效果。\n\n'
 for st,name in zip(studies,names):
  r=out[st]['Feedback + widening'];text+='- '+name+'：'+'；'.join(f"{t} {(r['ratios'][k]-1)*100:+.2f}%" for k,t in zip(keys,titles))+f"；额外报告 {r['cap_report_packets']} 个 / {r['cap_report_bytes']} B。\n"
 text+='\n原公平性窗口、Ring 的跨度/丢包/超时、完整 DP2 都继续保留；反馈报文的序列化字节数单独计数。独立观察重跑与相应无观测运行完全一致。所有数字都是同一开发种子的实测变化，未做统计持平声明。\n\n'
 text+='Hybrid 仍有回退：反馈校验延后了扩并发，但发送端限速在振荡中短暂恢复到线速时仍可能给出有效的正反馈。因此这不是完整解决方案，保持默认关闭，也不替换论文的最终结果。下一步需区分发送端 NIC 的多流竞争与网络拥塞，并验证持续条件；不能仅把短暂恢复解释为稳定可用容量。\n\n![](figures/feedback_changes.png)\n\n![](figures/feedback_cost.png)\n'
 with (ROOT/'REPORT.zh.md').open('a') as f:f.write(text)
 print('Feedback comparison and real protocol costs recorded for eleven scenes')
if __name__=='__main__':main()
