"""One global conditional-width intervention, with original fairness/Ring/DP2 metrics retained."""
import json
from pathlib import Path
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
ROOT=Path(__file__).resolve().parents[1]
def main():
 a=json.loads((ROOT/'analysis.json').read_text());idx={(r['study'],r['arm']):r for r in a['runs']}
 studies=['ali30','ali50','web40','fb40','fabric','receiver','hybrid','fairness','alltoall','ring','allreduce_dp2'];names=['Storage30','Storage50','Web','Analytics','Fabric','Receiver','Hybrid','Fairness','All-to-All','Ring','DP2']
 pairs={};old=json.loads((ROOT.parent/'guard_grantdiag_20260921/analysis.json').read_text());oi={(r['study'],r['arm']):r for r in old['runs']}
 for st in studies:
  b=idx[st,'width_shared_rescue'];n=idx[st,'width_adaptive_width']
  parent=oi[st,('fixed' if st in studies[:4] else 'width_scenes')+'_shared_rescue']
  pairs[st]=dict(before=b['metrics'],after=n['metrics'],exact_fct=b['fct_sha256']==n['fct_sha256'],exact_all_metrics=b['metrics']==n['metrics'],k1_cross_build_exact_fct=b['fct_sha256']==parent['fct_sha256'],k1_cross_build_exact_all_metrics=b['metrics']==parent['metrics'],bins_before=b['bins'],bins_after=n['bins'])
 def row(st,arm):return idx[st,'width_'+arm]
 fair={}
 for arm,name in [('shared_rescue','K1'),('adaptive_width','Conditional')]:
  r=row('fairness',arm);v=np.loadtxt(next(Path(r['output_dir']).glob('*_flow_bw.txt')),ndmin=2);f=np.loadtxt(r['fct_file'],ndmin=2)
  assert np.all(f[:,5]<=2010000000) and np.all(f[:,5]+f[:,6]>2012000000)
  rates=[];grids=[]
  for src in range(4):
   z=v[v[:,1]==src];grid=np.zeros(650);inds=np.rint(z[:,0]/100000).astype(int)-1;valid=(inds>=0)&(inds<650)
   assert len(np.unique(inds[valid]))==sum(valid);grid[inds[valid]]=z[valid,5];rates.append(float(grid[100:120].mean()));grids.append(grid.tolist())
  fair[name]=dict(jain=float(sum(rates)**2/(4*sum(x*x for x in rates))),rates=rates,grids=grids)
 result=dict(pairs=pairs,fairness=fair,stage='Observed development seed301 only; no statistical-tie claim')
 (ROOT/'width_comparison.json').write_text(json.dumps(result,indent=2)+'\n')
 def save(fig,name):
  fig.tight_layout()
  for ext in ['png','pdf']:fig.savefig(ROOT/'figures'/(name+'.'+ext),dpi=160)
  plt.close(fig)
 keys=['fct_mean_us','slowdown_p99','span_ms','queue_worst_port_fixed_mean_us'];labels=['Mean FCT','P99 slowdown','Trace span','Worst-port mean queue']
 fig,axs=plt.subplots(1,4,figsize=(16,7),sharey=True)
 for ax,k,label in zip(axs,keys,labels):
  vals=[pairs[st]['after'][k]/pairs[st]['before'][k] for st in studies]
  ax.scatter(vals,range(len(studies)),c=['#b94040' if v>1 else '#167c67' for v in vals]);ax.axvline(1,color='gray',ls='--')
  for i,v in enumerate(vals):ax.annotate(f'{(v-1)*100:+.3g}%',(v,i),xytext=(5,0),textcoords='offset points',fontsize=8,va='center')
  lo,hi=min(vals+[1]),max(vals+[1]);span=max(hi-lo,.1);ax.set_xlim(lo-span*.1,hi+span*.5);ax.set_title(label);ax.set_xlabel('Conditional / K1');ax.grid(alpha=.2)
 axs[0].set_yticks(range(len(studies)),names);axs[0].invert_yaxis();fig.suptitle('One global RTT-window service-width rule; all original scenes, development seed 301');save(fig,'width_changes')
 fig,axs=plt.subplots(2,3,figsize=(14,8))
 for ax,name in zip(axs[0,:2],['K1','Conditional']):
  for src,g in enumerate(fair[name]['grids']):ax.stairs(g,np.arange(651)*.1,label='Sender '+str(src))
  ax.set(title=f"{name}: original Jain={fair[name]['jain']:.6f}",xlabel='Time (ms)',ylabel='Send rate (Gb/s)',xlim=(0,65),ylim=(0,105));ax.grid(alpha=.2)
 axs[0,0].legend(ncol=2,fontsize=8);axs[0,2].axis('off');axs[0,2].text(.05,.5,'Original Jain window: 10–12 ms\n100 µs samples, zero-filled\nAll four flows active throughout\n\nRing: original span, drops and RTO',transform=axs[0,2].transAxes)
 for ax,k,label in zip(axs[1],['span_ms','drops','timeout_recoveries'],['Ring span (ms)','Ring dropped packets','Ring generic RTO events']):
  vals=[pairs['ring'][side][k] for side in ['before','after']];ax.bar(['K1','Conditional'],vals);ax.set_ylabel(label);ax.grid(axis='y',alpha=.2);ax.set_ylim(0,max(vals)*1.2+1)
  for i,v in enumerate(vals):ax.annotate(f'{v:.6g}',(i,v),xytext=(0,4),textcoords='offset points',ha='center')
 fig.suptitle('Original fairness and Ring metrics; same-source K1/Conditional, development seed 301');save(fig,'width_original_metrics')
 fig,axs=plt.subplots(1,2,figsize=(12,5))
 for arm,name in [('shared_rescue','K1'),('adaptive_width','Conditional')]:
  r=row('allreduce_dp2',arm);f=np.loadtxt(r['fct_file'],ndmin=2);assert len(f)==1280;x=np.sort(f[:,6]/1e6);axs[0].plot(x,np.arange(1,len(x)+1)/len(x),label=name)
  axs[1].plot(range(1,4),sorted((p['fixed_average_bytes']*8/100000 for p in r['ports']),reverse=True)[:3],marker='o',label=name)
 axs[0].set(xlabel='FCT (ms)',ylabel='CDF');axs[1].set(xlabel='Busiest port rank',ylabel='Fixed-window mean queue (µs)',xticks=[1,2,3])
 for ax in axs:ax.legend();ax.grid(alpha=.2)
 if pairs['allreduce_dp2']['exact_fct'] and pairs['allreduce_dp2']['exact_all_metrics']:
  axs[0].text(.45,.15,'K1 and Conditional match exactly',transform=axs[0].transAxes)
 fig.suptitle('Full DP2: 1280 flows, 80 buckets, original fixed observation; development seed 301');save(fig,'width_dp2')
 text='\n## 统一条件服务宽度实验\n\n只在连续两 RTT 到达速率低于线速 70% 时临时增加并发服务数，连续两 RTT 恢复到 85% 时退出。所有场景使用同一规则，12-BDP 阈值、128-BDP 服务范围及其他参数保持一致。以下均为开发样本。\n\n'
 for st,name in zip(studies,names):
  p=pairs[st];text+='- '+name+'：'+'；'.join(f"{label} {(p['after'][k]/p['before'][k]-1)*100:+.2f}%" for k,label in zip(keys,labels))+f"；丢包 {p['before']['drops']}→{p['after']['drops']}，超时 {p['before']['timeout_recoveries']}→{p['after']['timeout_recoveries']}。\n"
 text+=f"\n原公平性 Jain：K1 {fair['K1']['jain']:.6f}，Conditional {fair['Conditional']['jain']:.6f}。Ring 按原图跨度、丢包与超时评估，不用额外均值指标替代。完整 DP2 保留所有 1280 条流及原固定队列观测窗口。逐流和所有大小区间数据仍保留；本轮结果不能替代四基线独立确认。\n"
 text+='\n条件策略仍不能作为完整目标的最终配置：Hybrid 均值及队列退化，Web 和 Storage50 的队列也增加。Ring、Receiver 等未退化只说明改进了固定并发数为 2 的部分问题。保留所有变化，继续诊断 Hybrid；不按场景切换配置。四舍五入零不是统计持平结论，精确相同性另见 width_comparison.json。\n'
 with (ROOT/'REPORT.zh.md').open('a') as f:f.write(text)
 print('Wrote eleven-scene width comparison and three figures')
if __name__=='__main__':main()
