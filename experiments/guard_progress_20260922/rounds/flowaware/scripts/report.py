"""Record progress toward the unchanged figure-level goal, including failures."""
import json
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]


def main():
    data=json.loads((ROOT/'analysis.json').read_text())
    rows={(r['study'],r['arm']):r for r in data['runs']}
    def m(study,arm,metric):return rows[study,arm]['metrics'][metric]
    def change(study,a,b,metric):return 100*(m(study,a,metric)/m(study,b,metric)-1)
    candidate='shared_full_share128_window1'
    lines=['# GUARD 持续优化：开发轮证据','',
        '**目标仍未达成，保持进行中。** 所有原图都需要在原实验范围和四个基线下获得可验证的优势，或部分指标改善而其他指标持平。本轮没有把目标缩小为只改善 DP2 均值，也没有更新 Overleaf 为全面领先。','',
        f"本轮记录 {data['attempts']} 次尝试：{data['complete_original_trace_runs']} 次完整原轨迹仿真、{data['diagnostic_prefix_runs']} 次短前缀诊断，以及一次配置阶段失败。失败后保留原记录，另用相同仿真二进制、输入和参数补跑成功。",'',
        '所有运行使用已观察过的开发种子 301。以下变化是单个开发样本的测量，不能代替新种子的独立确认，也不提供虚假的置信区间。DP2 前缀只用于诊断，完整结果均来自原来的 1,280 流、每主机 2 GB 轨迹。','',
        '## 已取得的进展','',
        '单个发送端的多个长消息可以共享一个发送网卡额度，避免接收端再次把该网卡的额度分散到多个独立消息。当前试验仅在所有活跃消息来自同一发送端且都大于 128 BDP 时启用；加入第二个发送端或混入短消息时恢复原分配器。程序强制检查同速率、单网卡主机这一适用条件。','',
        f"完整 DP2：平均 FCT {m('allreduce_dp2',candidate,'fct_mean_us')/1000:.3f} ms，Homa {m('allreduce_dp2','shared_full_homa','fct_mean_us')/1000:.3f} ms，HPCC {m('allreduce_dp2','shared_full_hpcc','fct_mean_us')/1000:.3f} ms。",'',
        f"对 Homa，平均 FCT {change('allreduce_dp2',candidate,'shared_full_homa','fct_mean_us'):+.2f}%，完成跨度 {change('allreduce_dp2',candidate,'shared_full_homa','span_ms'):+.2f}%，固定窗口队列指标 {change('allreduce_dp2',candidate,'shared_full_homa','queue_worst_port_fixed_mean_us'):+.2f}%。该样本零丢包。",'',
        '## 仍然不满足目标的结果','',
        f"- DP2 长尾：共享额度的 P99 FCT {m('allreduce_dp2',candidate,'fct_p99_us')/1000:.3f} ms，Homa {m('allreduce_dp2','shared_full_homa','fct_p99_us')/1000:.3f} ms，变化 {change('allreduce_dp2',candidate,'shared_full_homa','fct_p99_us'):+.2f}%。CDF 保留交叉，均值领先没有覆盖长尾退化。",
        f"- DP2 队列：共享额度 {m('allreduce_dp2',candidate,'queue_worst_port_fixed_mean_us'):.3f} us，HPCC {m('allreduce_dp2','shared_full_hpcc','queue_worst_port_fixed_mean_us'):.3f} us。尚未同时达到 HPCC 的低队列。",
        f"- 存储 50%：降低剩余大小权重指数到 0 的均值为 {m('ali50','weights_weight0','fct_mean_us'):.3f} us，Homa 为 {m('ali50','storage_baselines_homa','fct_mean_us'):.3f} us，仍高 {change('ali50','weights_weight0','storage_baselines_homa','fct_mean_us'):.2f}%；P99 slowdown 仍高 {change('ali50','weights_weight0','storage_baselines_homa','slowdown_p99'):.2f}%。",
        '- Web、Analytics 和 All-to-All 没有出现一套共同配置可确认消除所有劣势。服务时间排序使部分 Web 指标改善，却使 All-to-All 平均 FCT 更差。',
        '- 本轮未做新种子的全部原图及四基线独立确认；此前的图 3/4 大消息尾部、组合消融的延迟/队列取舍等要求继续保留。','',
        '## 被否定的方向','',
        f"- 同源大消息逐个串行授权：完整 DP2 平均 FCT {m('allreduce_dp2','order_single_order','fct_mean_us')/1000:.3f} ms，明显差于本轮对照 {m('allreduce_dp2','reference_reference','fct_mean_us')/1000:.3f} ms。",
        '- 收到首个 grant 后扩大窗口到 2/4 BDP：没有稳定消除差距，多个场景队列或完成跨度回退。发送首个 grant 前仍以原 BDP 限制在途数据，记录中的门控与释放次数一致。',
        '- 将共享额度扩展到短消息：Ring 出现 9,606 次丢包，拒绝该配置。仅在长消息启用的开发样本保持 Ring 零丢包。',
        f"- 共享额度限制为 4 个并发消息：DP2 平均 FCT {m('allreduce_dp2','slots_full_slots4','fct_mean_us')/1000:.3f} ms，完成跨度 {m('allreduce_dp2','slots_full_slots4','span_ms'):.3f} ms。",
        f"- 限制为 8 个并发消息：DP2 P99 FCT {m('allreduce_dp2','slots_full_slots8','fct_p99_us')/1000:.3f} ms，仍未解决长尾。",
        '- 降低网络控制增益确实压低部分队列，但拉长完整 DP2 平均完成时间；不能按不同图挑选不同增益。','',
        '## 实现与复查入口','',
        '- `guard-flowaware` / `417eb4c`：同源顺序授权试验。',
        '- `guard-windowprobe` / `f6b2145`：首个 grant 后窗口和单源长消息共享额度试验。',
        '- `guard-servicetime` / `655dd5c`：按剩余字节与当前速率的比值选择发送消息。',
        '- `guard-sharedslots` / `5e171b1`：共享额度的有限活跃集合。',
        '- `guard-dirfix` / `0221ed7`：公共输出目录首次并行创建的修复，32 个并行 CLI 启动和 64 个私有目录碰撞请求通过验证。',
        '- `figures/dp2_full_metrics.pdf`、`figures/dp2_full_cdf.pdf`：完整 DP2 的均值、P99、跨度、队列和完整 CDF。',
        '- `figures/storage_weights.pdf`：存储权重试验及重测的 Homa、HPCC。',
        '- `analysis.json`、`validation_checks.json`、`raw_index.json`：全部尝试、身份核验、首次 grant 门控检查及原始归档哈希。','',
        '随机负载按输入开始时间采用原先固定的 5 ms 预热，保留全部合格流的完成记录。队列沿用固定观察窗口；串行授权方案的完成跨度超过该窗口，因此其队列指标不代表观察窗以外的尾段。各轮源代码提交与二进制冻结，轮间改变源代码会另建记录。','',
        '## 下一步保持的工作范围','',
        '优先用逐流拥塞反馈和实际发送服务轨迹解释共享额度方案的 DP2 长尾，区分路径拥塞、旧速率状态和发送端选择的影响。只有消除尾部与队列回退后，才冻结统一配置进行新种子复测。存储大消息、Web、Analytics、All-to-All、全部消融和补图继续在验收范围内。',
    ]
    (ROOT/'REPORT.zh.md').write_text('\n'.join(lines)+'\n')
    print('Wrote development report; objective remains active and unachieved')


if __name__=='__main__':main()
