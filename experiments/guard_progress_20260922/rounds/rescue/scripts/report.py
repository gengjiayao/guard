"""Show the complete stale-feedback repair effects, including every adverse metric."""
import json
from pathlib import Path
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
ROOT=Path(__file__).resolve().parents[1]
def main():
    a=json.loads((ROOT/'analysis.json').read_text());d=json.loads((ROOT/'diagnostic_analysis.json').read_text())
    idx={(r['study'],r['arm']):r for r in a['runs']}
    def row(arm,study='allreduce_dp2'):return idx[study,arm]
    def m(arm,k,study='allreduce_dp2'):return row(arm,study)['metrics'][k]
    def save(fig,name):
        fig.tight_layout()
        for ext in ['png','pdf']:fig.savefig(ROOT/'figures'/(name+'.'+ext),dpi=160)
        plt.close(fig)
    keys=['fct_mean_us','fct_p99_us','span_ms','queue_worst_port_fixed_mean_us'];labels=['Mean FCT (ms)','P99 FCT (ms)','Trace span (ms)','Worst-port mean queue (µs)'];scales=[.001,.001,1,1]
    profiles=['shared_cursor','shared_rescue','joint32_cursor','joint32_rescue','shared_l10_cursor','shared_l10_rescue']
    names=['Shared cursor','Shared rescue','Joint32 cursor','Joint32 rescue','Shared λ1 cursor','Shared λ1 rescue']
    arms=['dp2_'+p for p in profiles]
    def bars(arms,names,title,name):
        fig,axs=plt.subplots(2,2,figsize=(14,8))
        for ax,k,label,scale in zip(axs.flat,keys,labels,scales):
            vals=[m(arm,k)*scale for arm in arms];ax.bar(range(len(vals)),vals,color=plt.get_cmap('tab10')(np.arange(len(vals))%10))
            ax.set_xticks(range(len(vals)),names,rotation=35,ha='right');ax.set_ylabel(label);ax.set_ylim(0,max(vals)*1.16);ax.grid(axis='y',alpha=.2)
            for i,v in enumerate(vals):ax.annotate(f'{v:.2f}',(i,v),xytext=(0,3),textcoords='offset points',ha='center',fontsize=8)
        fig.suptitle(title+'\nFull original DP2; development seed 301; lower is better');save(fig,name)
    bars(arms,names,'Same-build stale partial ACK rescue controls','rescue_controls')
    bnames=names[:4]+['Homa','HPCC','DCQCN','TIMELY'];barms=arms[:4]+['dp2_'+p for p in ['homa','hpcc','dcqcn','timely']]
    bars(barms,bnames,'Same-build comparison with all four baselines','rescue_baselines')
    fig,ax=plt.subplots(figsize=(10,6))
    for arm,name in zip(barms,bnames):
        x=np.sort(np.loadtxt(row(arm)['fct_file'],ndmin=2)[:,6]/1e6);ax.plot(x,np.arange(1,len(x)+1)/len(x),label=name)
    ax.set(xlabel='Flow completion time (ms)',ylabel='CDF',title='Full original DP2: all 1,280 flows; development seed 301');ax.legend(ncol=2,fontsize=9);ax.grid(alpha=.2);save(fig,'rescue_cdf')
    fig,axs=plt.subplots(1,3,figsize=(15,5))
    for rank,ax in enumerate(axs):
        vals=[sorted((p['fixed_average_bytes']*8/100000 for p in row(arm)['ports']),reverse=True)[rank] for arm in barms]
        ax.bar(range(len(vals)),vals);ax.set_xticks(range(len(vals)),bnames,rotation=45,ha='right');ax.set_ylabel('Fixed-window mean queue (µs)');ax.set_title(f'Busiest port rank {rank+1}');ax.set_yscale('log');ax.grid(axis='y',alpha=.2)
    fig.suptitle('Full DP2: all three original queue ranks retained');save(fig,'queue_ranks')
    eventarms=arms+barms[4:];eventnames=names+bnames[4:]
    fig,axs=plt.subplots(3,1,figsize=(14,11),sharex=True)
    for ax,k,label in zip(axs[:2],['timeout_recoveries','pfc_pause_events'],['Generic RTO recovery events','PFC pause events']):
        vals=[m(arm,k) for arm in eventarms];ax.bar(range(len(vals)),vals);ax.set_ylabel(label);ax.set_yscale('symlog',linthresh=1);ax.set_ylim(0,max(vals)*5+1);ax.grid(axis='y',alpha=.2)
        for i,v in enumerate(vals):ax.annotate(str(v),(i,v),xytext=(0,3),textcoords='offset points',ha='center',fontsize=8)
    vals=[row(arm)['stats'].get('homa_resends_sent',0) for arm in eventarms];axs[2].bar(range(len(vals)),vals);axs[2].set_ylabel('Homa native RESENDs');axs[2].set_ylim(0,max(vals)*1.18);axs[2].grid(axis='y',alpha=.2)
    for i,(arm,v) in enumerate(zip(eventarms,vals)):axs[2].annotate(str(v) if arm.endswith('_homa') else 'n/a',(i,v),xytext=(0,3),textcoords='offset points',ha='center',fontsize=8)
    axs[2].set_xticks(range(len(vals)),eventnames,rotation=40,ha='right');fig.suptitle('Full DP2: recovery and pause counts; development seed 301');save(fig,'rescue_events')
    studies=['ali30','ali50','web40','fb40','alltoall','ring','fairness','fabric','receiver','hybrid'];snames=['Storage30','Storage50','Web','Analytics','All-to-All','Ring','Fairness','Fabric','Receiver','Hybrid']
    rkeys=['fct_mean_us','slowdown_p99','span_ms','queue_worst_port_fixed_mean_us'];changes={};fig,axs=plt.subplots(2,2,figsize=(14,8))
    for ax,k,label in zip(axs.flat,rkeys,['Mean FCT','P99 slowdown','Trace span','Worst-port mean queue']):
        for parent,phase,marker in [('shared','scenes','o'),('joint32','joint_cases','x')]:
            xs=[];ys=[]
            for i,study in enumerate(studies):
                if parent=='joint32' and study not in ['web40','fb40','alltoall','ring']:continue
                v=100*(m(phase+'_'+parent+'_rescue',k,study)/m(phase+'_'+parent+'_cursor',k,study)-1);xs.append(i);ys.append(v);changes.setdefault(study,{}).setdefault(parent,{})[k]=v
            ax.plot(xs,ys,marker=marker,linestyle='none',markersize=9,label=parent)
        ax.axhline(0,color='black',lw=.7);ax.set_xticks(range(10),snames,rotation=40,ha='right');ax.set_ylabel(label+' change (%)');ax.grid(alpha=.2)
    axs[0,0].legend();fig.suptitle('Rescue versus matched cursor: ten Shared scenes, four Joint32 scenes\nZero marks show exact measured differences; development seed 301');save(fig,'rescue_regression')
    fig,axs=plt.subplots(2,4,figsize=(16,8))
    for i,study in enumerate(['ali30','ali50']):
        for j,k in enumerate(['mean','95','99','99.9']):
            ax=axs[i,j]
            for suffix,style in [('cursor','-'),('rescue','--')]:
                bins=row('scenes_shared_'+suffix,study)['bins'];ax.plot(range(len(bins)),[b[k] if b['n'] else np.nan for b in bins],linestyle=style,marker='o' if suffix=='cursor' else 'x',label=suffix)
            ax.set_xticks(range(len(bins)),['4K','8K','16K','32K','64K','128K','256K','2M','>2M'],rotation=45);ax.set_yscale('log');ax.set_title(snames[i]+' '+('mean' if k=='mean' else 'P'+k));ax.set_ylabel('FCT slowdown');ax.grid(alpha=.2)
    axs[0,0].legend();fig.suptitle('Storage: all size bins retained; development seed 301\nBin counts in analysis.json; coincident curves are retained');save(fig,'storage_bins')
    fig,axs=plt.subplots(1,2,figsize=(12,5))
    for ax,k,label in zip(axs,['episodes','packets'],['Rescue episodes','Packets selected during rescue']):
        vals=[d['interventions'][row(arm)['key']][k] for arm in arms];ax.bar(range(len(vals)),vals);ax.set_xticks(range(len(vals)),names,rotation=35,ha='right');ax.set_ylabel(label);ax.set_ylim(0,max(vals)*1.2+1);ax.grid(axis='y',alpha=.2)
        for i,v in enumerate(vals):ax.annotate(str(v),(i,v),xytext=(0,3),textcoords='offset points',ha='center')
    fig.suptitle('Measured intervention counts; full DP2; development seed 301');save(fig,'rescue_activity')
    pairs={p:{k:100*(m('dp2_'+p+'_rescue',k)/m('dp2_'+p+'_cursor',k)-1) for k in keys} for p in ['shared','joint32','shared_l10']}
    (ROOT/'comparison.json').write_text(json.dumps(dict(dp2_percent=pairs,regression_percent=changes),indent=2)+'\n')
    text=f'''# GUARD 部分 ACK 批次的定向发送补足

完整论文优势目标仍在进行中。本轮 {a['attempts']} 次仿真均使用已经观察的开发种子 301，{a['completed']} 次完成，{len(a['failures'])} 次失败。全部采用原始输入和观察窗口，没有新种子独立确认或论文推广。

## 机制与实际测试

上一轮累计发送配额修复了局部饥饿，却增加 All-to-All 的平均延迟与队列。本轮保留普通 SRPT 调度，仅在非 IRN GUARD 流有不足一批 ACK 的在途字节、仍有待发字节、现有恢复定时器已进入后半周期且允许发送时补足该批次。

现有实现每发一个数据包都会重置恢复定时器。因此，触发后固定当前累计确认序列加原有 ACK 间隔作为目标，连续补齐至目标或流末尾。暂停、窗口、发送时间仍决定资格；收到确认、流结束或索引身份变化会释放过期状态。该选项默认关闭，不增加 ACK 定时器，也不修改 RTO 数值。半个 RTO 在观测前固定，没有逐场景扫描阈值。

实际调度器测试覆盖阈值前不干预、只处理部分批次、跨定时器重置补齐、八种排除条件及最早到期优先。完整仿真另外统计干预次数及实际选择的数据包数。

## 完整 DP2 与四基线

每次完整保留 1,280 条流、每主机 2 GB。三个 GUARD 父配置各做同构建配对，Homa、HPCC、DCQCN、TIMELY 使用相同构建及输入。

'''
    for arm,name in zip(eventarms,eventnames):
        text+=f"- {name}：平均 FCT {m(arm,keys[0])/1000:.3f} ms，P99 {m(arm,keys[1])/1000:.3f} ms，跨度 {m(arm,keys[2]):.3f} ms，队列 {m(arm,keys[3]):.3f} µs，通用超时恢复 {m(arm,'timeout_recoveries')}，PFC 暂停 {m(arm,'pfc_pause_events')}。\n"
    text+=f"\nHoma 另有 {row('dp2_homa')['stats']['homa_resends_sent']} 次原生 RESEND，通用 RTO 为零不代表没有重发。图见 figures/rescue_controls.pdf、rescue_baselines.pdf、rescue_cdf.pdf、queue_ranks.pdf 和 rescue_events.pdf。完整 CDF 与三个队列排名保留，单项改善不能替代其他指标。\n\n## 实际干预与跨场景结果\n\n"
    for arm,name in zip(arms,names):
        z=d['interventions'][row(arm)['key']];text+=f"- {name}：{z['episodes']} 次补足批次，{z['packets']} 个被选择的数据包。\n"
    for study,name in zip(studies,snames):
        for parent,v in changes[study].items():text+=f"- {name} / {parent}：平均 FCT {v[rkeys[0]]:+.4f}%，P99 slowdown {v[rkeys[1]]:+.4f}%，跨度 {v[rkeys[2]]:+.4f}%，队列 {v[rkeys[3]]:+.4f}%。\n"
    text+='\n原大小区间、均值与 P95/P99/P99.9 均保留，图见 storage_bins.pdf；跨场景变化见 rescue_regression.pdf。无干预配对另逐字节核对 FCT 和所有汇总指标，不把四舍五入的零当成统计持平。\n'
    text+=f"\n## 数据核验与剩余目标\n\n三个关闭新选项的 GUARD 控制及四个基线与前轮逐流 FCT、全部指标一致。诊断开关配对也一致，日志有 {d['completed_events']} 个匹配的完成事件，行数上限遗漏 {d['cap_omissions']}，观察到超时 {len(d['timeouts'])} 次。该日志实际 ACK 数为 {d['protocol']['252']['packets']}，序列化 ACK 字节为 {d['protocol']['252']['serialized_bytes']}，含包头、不含 IFG。\n"
    text+='''
源码冻结在 guard-ackrescue，完整修改与实际测试可复查。analysis.json、comparison.json、diagnostic_analysis.json、validation_checks.json、raw_index.json 保存数据、干预计数、日志与哈希验证；每轮同时保存驱动脚本副本。

全部原图的统一配置优势尚未得到证明。Storage 大消息、Web/Analytics、完整 DP2 长尾与低队列的冲突、All-to-All、组件消融及补图仍需继续处理。此次十场景回归用于判断新修改是否增加退化，不能代替各场景对四个基线的独立确认。论文图片和文字需要等完整证据成立后更新。
'''
    (ROOT/'REPORT.zh.md').write_text(text);print('Wrote eight figures and complete evidence report')
if __name__=='__main__':main()
