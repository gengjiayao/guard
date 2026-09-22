"""Keep the complete performance tradeoffs of ACK and scheduler repairs visible."""
import json,re
from pathlib import Path
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
ROOT=Path(__file__).resolve().parents[1]

def main():
    a=json.loads((ROOT/'analysis.json').read_text())
    idx={(r['study'],r['arm']):r for r in a['runs']}
    def row(arm,study='allreduce_dp2'):return idx[study,arm]
    def m(arm,key,study='allreduce_dp2'):return row(arm,study)['metrics'][key]
    keys=['fct_mean_us','fct_p99_us','span_ms','queue_worst_port_fixed_mean_us']
    labels=['Mean FCT (ms)','P99 FCT (ms)','Trace span (ms)','Worst-port mean queue (µs)']
    scales=[.001,.001,1,1]
    def save(fig,name):
        fig.tight_layout()
        for ext in ['png','pdf']:fig.savefig(ROOT/'figures'/(name+'.'+ext),dpi=160)
        plt.close(fig)
    def bars(arms,names,title,name):
        fig,axs=plt.subplots(2,2,figsize=(13,8))
        for ax,key,label,scale in zip(axs.flat,keys,labels,scales):
            vals=[m(arm,key)*scale for arm in arms]
            ax.bar(np.arange(len(arms)),vals,color=plt.get_cmap('tab10')(np.arange(len(arms))%10))
            ax.set_xticks(range(len(arms)),names)
            ax.set_ylabel(label);ax.tick_params(axis='x',rotation=35);ax.grid(axis='y',alpha=.2)
            ax.set_ylim(0,max(vals)*1.15)
            for i,v in enumerate(vals):ax.text(i,v,f'{v:.2f}',ha='center',va='bottom',fontsize=7)
        fig.suptitle(title+'; full DP2; development seed 301; lower is better');save(fig,name)
    arms=['bounded_shared','bounded_shared_deadline','bounded_joint32','bounded_joint32_deadline','bounded_homa','bounded_hpcc','bounded_dcqcn','bounded_timely']
    names=['Shared','Shared + deadline','Joint32','Joint32 + deadline','Homa','HPCC','DCQCN','TIMELY']
    bars(arms,names,'Matched-build ACK deadline and baseline comparison','deadline_baselines')
    fig,ax=plt.subplots(figsize=(9,5))
    for arm,name in zip(arms,names):
        x=np.sort(np.loadtxt(row(arm)['fct_file'],ndmin=2)[:,6]/1e6)
        ax.plot(x,np.arange(1,len(x)+1)/len(x),label=name)
    ax.set(xlabel='Flow completion time (ms)',ylabel='CDF',title='Full DP2; every flow retained; development seed 301')
    ax.legend(fontsize=8,ncol=2);ax.grid(alpha=.2);save(fig,'deadline_cdf')
    low_arms=['bounded_shared_l10','bounded_shared_l10_deadline','bounded_joint32_l10','bounded_joint32_l10_deadline',
              'idle_shared_l10','idle_shared_l10_deadline','idle_joint32_l10','idle_joint32_l10_deadline']
    low_names=['Shared λ1','Shared λ1 + deadline','Joint32 λ1','Joint32 λ1 + deadline','Shared λ1 + idle fix','Shared λ1 + both fixes','Joint32 λ1 + idle fix','Joint32 λ1 + both fixes']
    bars(low_arms,low_names,'ACK deadline and idle-timer controls (two labeled source revisions)','idle_controls')
    cursor_arms=['cursor_shared','cursor_shared_cursor','cursor_joint32','cursor_joint32_cursor','cursor_joint32_l10_deadline','cursor_joint32_l10_deadline_cursor']
    cursor_names=['Shared','Shared + cursor','Joint32','Joint32 + cursor','Joint32 λ1 + deadline','Joint32 λ1 + deadline + cursor']
    bars(cursor_arms,cursor_names,'Matched-build independent fairness cursor controls','cursor_controls')
    fig,axs=plt.subplots(2,1,figsize=(16,8),sharex=True)
    event_arms=arms+low_arms+['cursor_shared_cursor','cursor_joint32_cursor','cursor_joint32_l10_deadline_cursor']
    event_names=names+low_names+['Shared + cursor','Joint32 + cursor','Joint32 λ1 + deadline + cursor']
    for ax,key,label in zip(axs,['timeout_recoveries','pfc_pause_events'],['Timeout recovery events','PFC pause events']):
        vals=[m(arm,key) for arm in event_arms]
        ax.bar(range(len(vals)),vals);ax.set_xticks(range(len(vals)),event_names,rotation=55,ha='right')
        ax.set_ylabel(label);ax.set_yscale('symlog',linthresh=1);ax.grid(axis='y',alpha=.2)
        for i,v in enumerate(vals):ax.annotate(str(v),(i,v),xytext=(0,3),textcoords='offset points',ha='center',fontsize=7)
    fig.suptitle('Full DP2 event counts; development seed 301');save(fig,'recovery_events')
    studies=['ali30','ali50','web40','fb40','alltoall','ring','fairness','fabric','receiver','hybrid']
    snames=['Storage30','Storage50','Web','Analytics','All-to-All','Ring','Fairness','Fabric','Receiver','Hybrid']
    regkeys=['fct_mean_us','slowdown_p99','span_ms','queue_worst_port_fixed_mean_us']
    deltas={};fig,axs=plt.subplots(2,2,figsize=(13,8))
    for ax,key,label in zip(axs.flat,regkeys,['Mean FCT','P99 slowdown','Trace span','Worst-port mean queue']):
        vals=[]
        for study in studies:
            phase='smoke_fixed' if study in ['fb40','receiver','alltoall'] else 'regression'
            v=100*(m(phase+'_shared_deadline',key,study)/m(phase+'_shared',key,study)-1)
            vals.append(v);deltas.setdefault(study,{})[key]=v
        ax.bar(snames,vals);ax.set_ylabel(label+' change (%)');ax.tick_params(axis='x',rotation=40)
        ax.axhline(0,color='black',lw=.7);ax.grid(axis='y',alpha=.2)
    fig.suptitle('One-base-RTT ACK deadline versus matched Shared; ten original scenes; positive = worse')
    save(fig,'deadline_regression')
    cursor_deltas={};fig,axs=plt.subplots(2,2,figsize=(11,7))
    cursor_studies=['web40','fb40','alltoall','ring']
    for ax,key,label in zip(axs.flat,regkeys,['Mean FCT','P99 slowdown','Trace span','Worst-port mean queue']):
        for j,parent in enumerate(['shared','joint32']):
            vals=[]
            for study in cursor_studies:
                v=100*(m('cursor_cases_'+parent+'_cursor',key,study)/m('cursor_cases_'+parent,key,study)-1)
                vals.append(v);cursor_deltas.setdefault(study,{}).setdefault(parent,{})[key]=v
            ax.bar(np.arange(4)+(j-.5)*.35,vals,width=.34,label=parent)
        ax.set_xticks(range(4),['Web','Analytics','All-to-All','Ring']);ax.set_ylabel(label+' change (%)')
        ax.axhline(0,color='black',lw=.7);ax.grid(axis='y',alpha=.2)
    axs[0,0].legend();fig.suptitle('Independent fairness cursor versus matched parent; development seed 301; positive = worse')
    save(fig,'cursor_regression')
    deadline_stats={}
    for r in a['runs']:
        path=next(Path(r['output_dir']).glob('*_out_guard_stats.txt'))
        values=[]
        for line in path.read_text().splitlines():
            if line.startswith('guard_ack_deadline '):
                v=line.split()[1:];values.append(dict(zip(v[::2],v[1::2])))
        if not values:continue
        deadline_stats[r['key']]=dict(timers=sum(int(v['timers']) for v in values),
            sent=sum(int(v['sent']) for v in values),max_wait_ns=max(int(v['max_wait_ns']) for v in values))
    (ROOT/'comparison.json').write_text(json.dumps(dict(regression_percent=deltas,cursor_regression_percent=cursor_deltas,deadline_stats=deadline_stats),indent=2)+'\n')
    def desc(arm):
        return f"平均 FCT {m(arm,keys[0])/1000:.3f} ms，P99 {m(arm,keys[1])/1000:.3f} ms，跨度 {m(arm,keys[2]):.3f} ms，队列 {m(arm,keys[3]):.3f} µs，超时恢复 {m(arm,'timeout_recoveries')}，PFC 暂停 {m(arm,'pfc_pause_events')}。"
    text=f'''# GUARD ACK 等待、空闲超时与发送轮询实验

完整论文优势目标仍在进行中。本轮共记录 {a['attempts']} 次运行尝试，{a['completed']} 次完整仿真，{len(a['failures'])} 次配置或实现失败均保留。全部使用已经观察的开发种子 301，尚未独立确认，也没有推广到 Overleaf。

## 诊断与修复

- 完整 DP2 的两组低增益对照共有 18 次超时：17 次剩余 1–7 KB 未确认，1 次已无在途数据。17 次均不足原本每 8 包的一批 ACK；发送期限早已到达，但流没有得到持续发送机会。仅凭这些日志不把所有尾延迟归结为一个原因。
- ACK 合并原本没有部分批次的等待上限。新增可选的一倍 base RTT 上限，从首个被合并的包计时，携带最新收到的 INT；常规 ACK/NACK、完成及删除接收状态时取消定时器。最初原型保留了随后被上层修改的包，三次功能检查失败；修复为保留包副本并明确解析 INT，重跑的六次检查全部完成。
- 对普通 GUARD 传输，确认全部在途字节后取消旧恢复定时器，并保护超时入口免于对零在途数据执行恢复。实际函数测试验证未确认数据和 IRN 的定时器保持有效，RTO 数值没有改动。
- 实际发送调度器的四流复现中，650 次发送原先分为 640/10/0/0。每 64 包一次的让步反复选择最短流的相邻流。新增独立轮询游标后为 640/4/3/3，并验证暂停、发送时间、窗口及完成状态的限制仍有效。

## ACK 实际链路字节

主机 PHY 发送计数表明，ACK8 为约 0.376 GB ACK，ACK1 为 3.008 GB ACK；数据包本身含头部约 34.880 GB。统计包含序列化包头、不包含 IFG，不能直接当作精确链路忙碌时间。ACK1 两组的控制字节占比约 8.4–8.5%，ACK8 约 1.5%。这是实际开销证据，尚未单独隔离开销与反馈时序各自对性能的贡献。

所有初始日志开关配对的逐流 FCT 和全部汇总指标相同。两条 ACK1 控制日志达到 300,000 行上限；保留原记录，并以 1 ms 采样补跑。超时和完成事件不受时间采样限制，补跑同样核对逐流 FCT、指标和全部完成事件。见 diagnostic_analysis.json 和 figures/timeout_wire_diagnosis.pdf。

## 完整 DP2 与四个基线

下列为 ACK 等待上限版本的同源码比较；完整 1,280 条流、原有输入和固定观察窗口均保留。

'''
    for arm,name in zip(arms,names):text+=f'- {name}：{desc(arm)}\n'
    text+='\nJoint32 加 ACK 等待上限虽然降低了平均和 P99 FCT，却触发 7,460 次 PFC 暂停，队列也增大；不能作为全面优势的结论。Homa 在不同源码构建中的结果仍有波动，此处仅使用本次同版本测量；后续还需检查其重发扫描顺序的确定性。\n'
    text+='\n完整分布见 figures/deadline_cdf.pdf；均值、尾部、跨度和队列同时保留，不能只选择改善的指标。\n\n## 低增益与空闲定时器修复\n\n'
    for arm,name in zip(low_arms,low_names):text+=f'- {arm}（{name}）：{desc(arm)}\n'
    text+='\n## 独立轮询游标的同版本配对\n\n'
    for arm,name in zip(cursor_arms,cursor_names):text+=f'- {arm}（{name}）：{desc(arm)}\n'
    text+='''
游标版本完成了 Web、Analytics、All-to-All、Ring 的两组同版本配对回归，尚未完成十个原始场景及四基线的全套独立复测，因此不能借用前一个版本的结果宣称新版本全面领先。图见 figures/cursor_controls.pdf 和 cursor_regression.pdf。单元测试证明轮询缺陷得到修复，不能代替真实性能验证。

'''
    for study in cursor_studies:
        for parent in ['shared','joint32']:
            d=cursor_deltas[study][parent]
            text+=f"- {study} / {parent} 加游标：平均 FCT {d[regkeys[0]]:+.2f}%，P99 slowdown {d[regkeys[1]]:+.2f}%，跨度 {d[regkeys[2]]:+.2f}%，队列 {d[regkeys[3]]:+.2f}%。\n"
    text+='''

## ACK 等待上限的十场景回归

以下是同版本 Shared 的变化，正数表示退化；完整图见 figures/deadline_regression.pdf。

'''
    for s,name in zip(studies,snames):
        d=deltas[s];text+=f"- {name}：平均 FCT {d[regkeys[0]]:+.2f}%，P99 slowdown {d[regkeys[1]]:+.2f}%，跨度 {d[regkeys[2]]:+.2f}%，队列 {d[regkeys[3]]:+.2f}%。\n"
    text+='''
## 证据与剩余范围

所有配置生成失败、崩溃、截断日志及补跑分别保留，没有覆盖或挑选成功运行。最初启动还因缺失 runs 目录提前失败，记录在 bootstrap-failed.log；此时尚未产生单项运行记录。分析入口为 analysis.json、diagnostic_analysis.json、comparison.json、validation_checks.json、raw_index.json；每轮保存当时的完整驱动脚本副本。

下一步围绕实际轮询修复与网络反馈的交互继续优化，处理队列与尾延迟的取舍。原论文所有负载、大小分组、网络/接收/混合拥塞、严格消融、OFLM、公平性、All-to-All、完整 DP2、Ring 及两组补图仍需统一配置和四基线复测。独立种子确认与论文文字、图片更新尚未完成。
'''
    (ROOT/'REPORT.zh.md').write_text(text)
    print('Wrote seven complete comparison figures and report; performance goal remains active')

if __name__=='__main__':main()
