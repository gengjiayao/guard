"""Write a complete outcome report, including adverse and inconclusive results."""
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def main():
    gate = json.loads((ROOT/'validation_checks.json').read_text())
    assert gate['status']=='passed'
    data = json.loads((ROOT/'confirmation-evidence.json').read_text())
    comparisons = {(x['study'],x['baseline'],x['metric']):x for x in data['comparisons']}
    def result(study,baseline,metric):
        x = comparisons.get((study,baseline,metric))
        if not x:
            return '无可计算的五种子配对百分比'
        lo,hi=x['ci95'];v=x['percent_change']
        outcome = '更低' if hi<0 else '更高' if lo>0 else '差异区间跨零或为零'
        return f'{v:+.2f}%（95% 区间 {lo:+.2f}% 至 {hi:+.2f}%；{outcome}）'
    f=data['fairness']
    lines=[
        '# GUARD 后续优化：完整复测与未解决问题',
        '',
        '本轮完成了实现修改、全部原有实验族的复测、严格组件消融和四个外部基线比较。结果包含明确收益、持平和回退，不能据此声称每张图或每个指标都全面领先。',
        '',
        f"开发记录 {gate['development_attempts']} 次尝试，其中 {gate['completed_development_runs']} 次完整仿真；独立验证 {gate['confirmation_runs']} 次完整仿真。开发中一次输出目录碰撞失败已原样保留，修复后另行重测。独立验证无失败、无遗漏完成记录。",
        '',
        '开发使用已观察过的种子 301。源代码和一套全局参数在验证前冻结，独立验证使用新种子 501–505，没有根据验证结果重新调参，也没有为不同图选择不同配置。',
        '',
        '源代码：`/home/gengjiayao/ict/guard-balanced-cohort`；冻结提交：`0e3208af4eb6c15da47cc41ab44a712daa883122`。配置与全部哈希见 `holdout/confirmation-manifest.json`。额外 8 次接收端双发送者时间序列复测见 `holdout/series-manifest.json`，只增加监测，算法和参数相同。',
        '',
        '## 修复与机制证据',
        '',
        '- 修复并发限制分支忽略公平带宽下限的问题。对实际 C++ 分配器验证 1,000 组状态，检查预算、最低份额、插入顺序、同源消息、混合大小和不同 RTT。',
        '- 以接收端统一的服务范围区分长流共享与短流优先；保留同一发送端长消息的剩余大小排序，并限制混合优先级集合的串行化。',
        '- 尾部阶段继续处理网络拥塞反馈，保持此前的 Ring 丢包修复。',
        '- 新增只关闭网络侧反馈的 receiver-only 对照。旧模式同时改变 ACK 频率、窗口和发送端调度，仍保留为 legacy 对照。配置差异检查确认新对照只改变 `GUARD_FABRIC_CONTROL`。',
        '- 修复实验输出目录的并发创建冲突。64 个相同目录编号的并行申请得到 64 个独立目录，既有文件保持完整。',
        '',
        '## 原图逐项复测结果',
        '',
        '图 1 是架构图，不承担性能优越性的实验证明。以下百分比以更低为好；每项采用五个相同种子的逐对比值变化。',
        '',
        '随机负载沿用预先固定的 5 ms 预热：FCT 和 slowdown 统计起始时间晚于 2.005 s 的流，保留这些流的所有完成记录。定向和集合通信场景无预热。输入起始时间决定统计资格，完成时间不参与筛选；所有输入流仍需完成并通过身份校验。包含预热流的均值另存于 `raw-fct-spot-check.json`，不与图中口径混用。',
        '',
        '### 图 2：随机负载',
        '',
    ]
    for s,name in [('ali30','存储 30%'),('ali50','存储 50%'),('web40','Web search'),('fb40','Analytics')]:
        lines += [f'- {name}：平均 FCT 对 Homa {result(s,"homa","fct_mean_us")}；P99 slowdown 对 Homa {result(s,"homa","slowdown_p99")}；平均 FCT 对旧 GUARD {result(s,"old_guard","fct_mean_us")}。']
    lines += ['', '### 图 3、4：存储分桶尾部', '',
        '重新绘制平均、P95、P99 和 P99.9 slowdown 的全部非空大小桶，保留不利结果。分桶配对比较见 `holdout/audit/figure-advantage-effects.json`；P99.9 仍是受桶内样本数限制的描述性极端尾部统计。', '']
    audit = json.loads((ROOT/'holdout/audit/figure-advantage-effects.json').read_text())
    for study,name in [('ali30','存储 30%'),('ali50','存储 50%')]:
        for metric,label in [('mean','平均'),('95','P95'),('99','P99'),('99.9','P99.9')]:
            items = [x for x in audit['comparisons'] if x['study']==study
                     and x['baseline']=='homa' and x['metric']=='bin_slowdown_'+metric]
            assert len(items)==8, (study,metric,len(items))
            slower = [x for x in items if x['ci95'][0]>0]
            unclear = [x for x in items if x['ci95'][0]<=0<=x['ci95'][1]]
            faster = [x for x in items if x['ci95'][1]<0]
            details = '；'.join(f"上界 {x['hi']/1000:g} kB：{x['percent_change']:+.1f}%"
                               for x in slower)
            lines += [f'- {name} {label} slowdown 对 Homa：{len(faster)} 个桶的区间低于零，'
                      f'{len(unclear)} 个桶区间含零，{len(slower)} 个桶区间高于零。'
                      + ('回退桶：'+details+'。' if details else '')]
    lines += ['', '### 图 5 与补图 2：瓶颈位置和发送者数量', '']
    for s,name in [('fabric','仅共享网络瓶颈'),('receiver2','两个发送者汇聚'),('receiver','四个发送者汇聚'),('hybrid','混合瓶颈')]:
        lines += [f'- {name}：平均 FCT 对 Homa {result(s,"homa","fct_mean_us")}；队列指标对 Homa {result(s,"homa","queue_worst_port_fixed_mean_us")}。']
    lines += ['', '### 图 6：严格的组合消融', '',
        f'混合瓶颈中，完整 GUARD 对严格 receiver-only 的平均 FCT {result("hybrid","receiver_only","fct_mean_us")}；队列指标 {result("hybrid","receiver_only","queue_worst_port_fixed_mean_us")}；完成跨度 {result("hybrid","receiver_only","span_ms")}。', '',
        '同时保留旧 receiver-only、保留最后一跳 INT、lambda=1 和 lambda=1.4 的对照。绑定次数只表示机制活动，不能代替性能收益。', '',
        '### 图 7：OFLM', '']
    for arm,name in [('no_selective','关闭选择性注册'),('no_release','关闭主动释放'),('no_oflm','同时关闭两项')]:
        lines += [f'- 对{name}：平均 FCT {result("ali50",arm,"fct_mean_us")}；grant 消息数 {result("ali50",arm,"grants")}；平均流速率（越高越好）{result("ali50",arm,"mean_flow_goodput_gbps")}。']
    lines += ['', '### 图 8：公平性及其代价', '',
        f'固定 10–12 ms 窗口 Jain 指数：新 GUARD {f["guard"]["mean"]:.6f}，旧 GUARD {f["old_guard"]["mean"]:.6f}，Homa {f["homa"]["mean"]:.6f}，TIMELY {f["timely"]["mean"]:.6f}。', '',
        f'该场景平均 FCT 对旧 GUARD {result("fairness","old_guard","fct_mean_us")}；对 Homa {result("fairness","homa","fct_mean_us")}。公平性改善不能被写成所有延迟指标同时改善。', '',
        '### 图 9：集合通信轨迹', '']
    for s,name in [('alltoall','All-to-All'),('allreduce_dp2','DP2')]:
        lines += [f'- {name}：对 Homa 的完成跨度 {result(s,"homa","span_ms")}，平均 FCT {result(s,"homa","fct_mean_us")}；平均 FCT 对旧 GUARD {result(s,"old_guard","fct_mean_us")}。']
    lines += ['', '轨迹采用开环注入，因此这里的完成跨度不是训练任务 JCT。', '',
        '### 图 10：Ring', '',
        f'对 Homa：完成跨度 {result("ring","homa","span_ms")}；平均 FCT {result("ring","homa","fct_mean_us")}；队列指标 {result("ring","homa","queue_worst_port_fixed_mean_us")}。丢包和恢复次数见原始计数及 Ring 图，零值未用于百分比除法。另绘制 `figures/per_experiment/ring_latency_queue.pdf`，同时呈现平均 FCT 与队列代价。', '',
        f'对严格 receiver-only：平均 FCT {result("ring","receiver_only","fct_mean_us")}；完成跨度 {result("ring","receiver_only","span_ms")}；队列指标 {result("ring","receiver_only","queue_worst_port_fixed_mean_us")}。两者在五个种子均无丢包，因此本轮不能把无丢包归因于网络侧反馈的独有作用。', '',
        '### 补图 1：时间序列', '',
        '使用固定首个验证种子 501，保留 fabric、双发送者汇聚、混合瓶颈的发送速率与队列曲线，展示机制行为。单条轨迹不能证明跨种子一致领先。', '',
        '## 图和复查入口', '',
        '- `figures/optimization_effects.pdf`：相对旧 GUARD 的平均 FCT、完成跨度、队列变化。',
        '- `figures/baseline_comparison.pdf`：与 HPCC、Homa、DCQCN、TIMELY 的平均 FCT 配对比较。',
        '- `figures/safety_and_fairness.pdf`：公平性、Ring 完成跨度与丢包。',
        '- `figures/per_experiment/`：全部原实验族的向量图及 PNG。',
        '- `confirmation-evidence.json`：配对结果、区间和来源运行编号。',
        '- `validation_checks.json`、`raw_index.json`：完成完整性、严格消融配置差异和所有原始归档的哈希。', '',
        '区间采用 t(4) 的逐项 95% 置信区间，未作多重比较校正。所有比较保留同一输入身份、拓扑、缓冲区与监测口径。没有筛掉慢流或按协议设置不同完成截止时间。', '',
        '## 采用决定', '',
        '该候选仍包含未解决的延迟回退和公平性取舍，因此保留在实验分支，未作为统一默认配置合并，也未将 Overleaf 改写为全面领先。此前 401–405 验证中缺少的 75 次外部基线和 OFLM 运行另行补齐，其结果与本轮新种子证据分别保存。',
    ]
    (ROOT/'REPORT.zh.md').write_text('\n'.join(lines)+'\n')
    print('Wrote REPORT.zh.md with all original figure families and adverse results')


if __name__=='__main__':
    main()
