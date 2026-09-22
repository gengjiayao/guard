"""Report the aggregate-service repair separately from the rejected batch-only change."""
import json
from pathlib import Path
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
ROOT=Path(__file__).resolve().parents[1]
def main():
    a=json.loads((ROOT/'analysis.json').read_text());idx={(r['study'],r['arm']):r for r in a['runs']}
    def row(arm,study='allreduce_dp2'):return idx[study,arm]
    def m(arm,k,study='allreduce_dp2'):return row(arm,study)['metrics'][k]
    def save(fig,name):
        fig.tight_layout()
        for ext in ['png','pdf']:fig.savefig(ROOT/'figures'/(name+'.'+ext),dpi=160)
        plt.close(fig)
    ps=['shared_cursor','shared_budget','shared_budget_batch','joint32_cursor','joint32_budget','shared_l10_cursor','shared_l10_budget','shared_l10_budget_batch']
    names=['Shared cursor','Shared budget','Shared budget + batch','Joint32 cursor','Joint32 budget','Shared λ1 cursor','Shared λ1 budget','Shared λ1 budget + batch']
    arms=['budget_dp2_'+p for p in ps]
    keys=['fct_mean_us','fct_p99_us','span_ms','queue_worst_port_fixed_mean_us','timeout_recoveries','pfc_pause_events']
    labels=['Mean FCT (ms)','P99 FCT (ms)','Trace span (ms)','Worst-port mean queue (µs)','Timeout recoveries','PFC pause events']
    scales=[.001,.001,1,1,1,1]
    fig,axs=plt.subplots(2,3,figsize=(18,10))
    for ax,k,label,scale in zip(axs.flat,keys,labels,scales):
        vals=[m(arm,k)*scale for arm in arms]
        ax.bar(range(len(arms)),vals,color=plt.get_cmap('tab10')(np.arange(len(arms))));ax.set_xticks(range(len(arms)),names,rotation=45,ha='right')
        ax.set_ylabel(label);ax.grid(axis='y',alpha=.2)
        if k in ['timeout_recoveries','pfc_pause_events']:
            ax.set_yscale('symlog',linthresh=1);ax.set_ylim(0,max(vals)*1.6+1)
        else:ax.set_ylim(0,max(vals)*1.16)
        for i,v in enumerate(vals):ax.annotate(f'{v:.2f}' if scale!=1 or k not in ['timeout_recoveries','pfc_pause_events'] else str(int(v)),(i,v),xytext=(0,3),textcoords='offset points',ha='center',fontsize=7)
    fig.suptitle('Aggregate service budget: same-build controls; full original DP2; development seed 301');save(fig,'budget_controls')
    fig,ax=plt.subplots(figsize=(11,6))
    carms=['budget_dp2_shared_cursor','budget_dp2_shared_budget','budget_dp2_shared_budget_batch','budget_dp2_joint32_budget','budget_dp2_homa','batch_dp2_hpcc','batch_dp2_dcqcn','batch_dp2_timely']
    cnames=['Shared cursor','Shared budget','Shared budget + batch','Joint32 budget','Homa','HPCC (prior build)','DCQCN (prior build)','TIMELY (prior build)']
    for arm,name in zip(carms,cnames):
        x=np.sort(np.loadtxt(row(arm)['fct_file'],ndmin=2)[:,6]/1e6)
        ax.plot(x,np.arange(1,len(x)+1)/len(x),label=name)
    ax.set(xlabel='Flow completion time (ms)',ylabel='CDF',title='Full original DP2: every flow retained; development seed 301')
    ax.legend(fontsize=9,ncol=2);ax.grid(alpha=.2);save(fig,'budget_cdf')
    studies=['web40','fb40','alltoall','ring','ali30','ali50'];snames=['Web','Analytics','All-to-All','Ring','Storage30','Storage50']
    rkeys=['fct_mean_us','slowdown_p99','span_ms','queue_worst_port_fixed_mean_us']
    deltas={};fig,axs=plt.subplots(2,2,figsize=(13,8))
    for ax,k,label in zip(axs.flat,rkeys,['Mean FCT','P99 slowdown','Trace span','Worst-port mean queue']):
        for j,parent in enumerate(['shared','joint32']):
            xs=[];vals=[]
            for i,study in enumerate(studies):
                if parent=='joint32' and i>=4:continue
                phase='budget_cases' if i<4 else 'budget_storage'
                v=100*(m(phase+'_'+parent+'_budget',k,study)/m(phase+'_'+parent+'_cursor',k,study)-1)
                xs.append(i+(j-.5)*.35);vals.append(v);deltas.setdefault(study,{}).setdefault(parent,{})[k]=v
            ax.bar(xs,vals,width=.34,label=parent)
        ax.set_xticks(range(6),snames,rotation=30,ha='right');ax.set_ylabel(label+' change (%)');ax.axhline(0,color='black',lw=.7);ax.grid(axis='y',alpha=.2)
    axs[0,0].legend();fig.suptitle('Aggregate service budget versus matched cursor; positive = worse\nJoint32 Storage not measured in this round');save(fig,'budget_regression')
    fig,axs=plt.subplots(2,4,figsize=(16,8))
    for i,study in enumerate(['ali30','ali50']):
        for j,k in enumerate(['mean','95','99','99.9']):
            ax=axs[i,j]
            for suffix in ['cursor','budget']:
                bins=row('budget_storage_shared_'+suffix,study)['bins']
                ax.plot(range(len(bins)),[b[k] if b['n'] else np.nan for b in bins],marker='o',label=suffix)
            ax.set_xticks(range(len(bins)),['4K','8K','16K','32K','64K','128K','256K','2M','>2M'],rotation=45)
            ax.set_yscale('log');ax.set_title(snames[4+i]+' '+('mean' if k=='mean' else 'P'+k))
            ax.set_ylabel('FCT slowdown');ax.grid(alpha=.2)
    axs[0,0].legend();fig.suptitle('Storage with aggregate service budget: all original size bins retained\nDevelopment seed 301; bin counts retained in analysis.json');save(fig,'budget_storage_bins')
    pairs={parent:{k:100*(m('budget_dp2_'+parent+'_budget',k)/m('budget_dp2_'+parent+'_cursor',k)-1) for k in keys[:4]} for parent in ['shared','joint32','shared_l10']}
    (ROOT/'budget_comparison.json').write_text(json.dumps(dict(dp2_percent=pairs,regression_percent=deltas),indent=2)+'\n')
    text='''
## 累计发送配额修复

批次调度的完整结果仍有退化，进一步复现发现：两个短流交替满足发送条件时，旧“连续同一流 64 包”的规则永远不触发让步。实际调度器中，始终合格的第三个长流在 650 次发送中获得 0 次服务，分配为 325/325/0。累计所有优先发送包数后，在既有 64 包量子后执行一次公平发送；同一复现变为 320/320/10，在批次开关关闭和开启时均成立。

选项 guard_sender_service_budget 默认关闭，要求独立公平游标。实际测试同时保留单一最短流时的 64:1 份额、原批次补齐及资格排除测试。发送累计计数在流身份切换时保留，只在确实选择其他合格流后清零；没有其他合格流时继续服务，保持到期让步状态。

以下是新构建的完整 DP2 同版本配对；没有按场景选择不同的量子。

'''
    for arm,name in zip(arms,names):
        text+=f"- {name}：平均 FCT {m(arm,keys[0])/1000:.3f} ms，P99 {m(arm,keys[1])/1000:.3f} ms，跨度 {m(arm,keys[2]):.3f} ms，队列 {m(arm,keys[3]):.3f} µs，超时恢复 {m(arm,keys[4])}，PFC {m(arm,keys[5])}。\n"
    text+='\n新构建 Homa 与前一构建和全部固定重发顺序检查一致。三个关闭新选项的 GUARD DP2 控制也逐流一致。CDF 中 HPCC、DCQCN 和 TIMELY 明确标为前一构建参照，本次未重复它们，不能描述为新构建全基线确认。图见 figures/budget_controls.pdf、budget_cdf.pdf 和 budget_regression.pdf、budget_storage_bins.pdf。\n\n'
    for study,name in zip(studies,snames):
        for parent,d in deltas[study].items():text+=f"- {name} / {parent}：平均 FCT {d[rkeys[0]]:+.2f}%，P99 slowdown {d[rkeys[1]]:+.2f}%，跨度 {d[rkeys[2]]:+.2f}%，队列 {d[rkeys[3]]:+.2f}%。\n"
    diag=json.loads((ROOT/'diagnostic_analysis.json').read_text())
    text+='\n## 完整诊断日志\n\n'
    for d in diag:
        text+=f"- Shared λ1 / {d['variant']}：{len(d['timeouts'])} 次超时，在途字节依次为 {[v['outstanding_bytes'] for v in d['timeouts']]}；ACK {d['protocol']['252']['packets']} 个，序列化 ACK 字节 {d['protocol']['252']['serialized_bytes']}。\n"
    text+='\n三组日志配对均核对逐流 FCT 和全部指标一致，完成事件各 1,280 个，无达到上限而遗漏的事件。字节数含包头、不含 IFG。修复调度缺陷不等于已实现所有原图全面优势；新种子确认、全实验统一配置和论文更新仍未完成。\n'
    with (ROOT/'REPORT.zh.md').open('a') as f:f.write(text)
    print('Wrote four service-budget figures and appended honest paired results')
if __name__=='__main__':main()
