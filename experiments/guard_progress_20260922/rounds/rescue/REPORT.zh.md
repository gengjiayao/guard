# GUARD 部分 ACK 批次的定向发送补足

完整论文优势目标仍在进行中。本轮 83 次仿真均使用已经观察的开发种子 301，83 次完成，0 次失败。全部采用原始输入和观察窗口，没有新种子独立确认或论文推广。

## 机制与实际测试

上一轮累计发送配额修复了局部饥饿，却增加 All-to-All 的平均延迟与队列。本轮保留普通 SRPT 调度，仅在非 IRN GUARD 流有不足一批 ACK 的在途字节、仍有待发字节、现有恢复定时器已进入后半周期且允许发送时补足该批次。

现有实现每发一个数据包都会重置恢复定时器。因此，触发后固定当前累计确认序列加原有 ACK 间隔作为目标，连续补齐至目标或流末尾。暂停、窗口、发送时间仍决定资格；收到确认、流结束或索引身份变化会释放过期状态。该选项默认关闭，不增加 ACK 定时器，也不修改 RTO 数值。半个 RTO 在观测前固定，没有逐场景扫描阈值。

实际调度器测试覆盖阈值前不干预、只处理部分批次、跨定时器重置补齐、八种排除条件及最早到期优先。完整仿真另外统计干预次数及实际选择的数据包数。

## 完整 DP2 与四基线

每次完整保留 1,280 条流、每主机 2 GB。三个 GUARD 父配置各做同构建配对，Homa、HPCC、DCQCN、TIMELY 使用相同构建及输入。

- Shared cursor：平均 FCT 15.669 ms，P99 88.793 ms，跨度 216.534 ms，队列 12.478 µs，通用超时恢复 0，PFC 暂停 0。
- Shared rescue：平均 FCT 15.671 ms，P99 85.401 ms，跨度 215.002 ms，队列 12.259 µs，通用超时恢复 0，PFC 暂停 0。
- Joint32 cursor：平均 FCT 16.450 ms，P99 58.835 ms，跨度 216.961 ms，队列 24.707 µs，通用超时恢复 0，PFC 暂停 26。
- Joint32 rescue：平均 FCT 16.450 ms，P99 58.835 ms，跨度 216.961 ms，队列 24.707 µs，通用超时恢复 0，PFC 暂停 26。
- Shared λ1 cursor：平均 FCT 24.482 ms，P99 103.222 ms，跨度 227.558 ms，队列 5.313 µs，通用超时恢复 3，PFC 暂停 0。
- Shared λ1 rescue：平均 FCT 24.338 ms，P99 103.637 ms，跨度 226.592 ms，队列 2.905 µs，通用超时恢复 0，PFC 暂停 0。
- Homa：平均 FCT 18.146 ms，P99 45.688 ms，跨度 230.976 ms，队列 53.810 µs，通用超时恢复 0，PFC 暂停 0。
- HPCC：平均 FCT 28.677 ms，P99 72.094 ms，跨度 226.362 ms，队列 0.213 µs，通用超时恢复 0，PFC 暂停 0。
- DCQCN：平均 FCT 25.343 ms，P99 77.993 ms，跨度 224.544 ms，队列 4.626 µs，通用超时恢复 0，PFC 暂停 0。
- TIMELY：平均 FCT 39.089 ms，P99 84.885 ms，跨度 240.235 ms，队列 16.592 µs，通用超时恢复 0，PFC 暂停 3873。

Homa 另有 10618 次原生 RESEND，通用 RTO 为零不代表没有重发。图见 figures/rescue_controls.pdf、rescue_baselines.pdf、rescue_cdf.pdf、queue_ranks.pdf 和 rescue_events.pdf。完整 CDF 与三个队列排名保留，单项改善不能替代其他指标。

## 实际干预与跨场景结果

- Shared cursor：0 次补足批次，0 个被选择的数据包。
- Shared rescue：6 次补足批次，28 个被选择的数据包。
- Joint32 cursor：0 次补足批次，0 个被选择的数据包。
- Joint32 rescue：0 次补足批次，0 个被选择的数据包。
- Shared λ1 cursor：0 次补足批次，0 个被选择的数据包。
- Shared λ1 rescue：30 次补足批次，121 个被选择的数据包。
- Storage30 / shared：平均 FCT +0.0000%，P99 slowdown +0.0000%，跨度 +0.0000%，队列 +0.0000%。
- Storage50 / shared：平均 FCT +0.0000%，P99 slowdown +0.0000%，跨度 +0.0000%，队列 +0.0000%。
- Web / shared：平均 FCT +0.0000%，P99 slowdown +0.0000%，跨度 +0.0000%，队列 +0.0000%。
- Web / joint32：平均 FCT +0.0000%，P99 slowdown +0.0000%，跨度 +0.0000%，队列 +0.0000%。
- Analytics / shared：平均 FCT +0.0000%，P99 slowdown +0.0000%，跨度 +0.0000%，队列 +0.0000%。
- Analytics / joint32：平均 FCT +0.0000%，P99 slowdown +0.0000%，跨度 +0.0000%，队列 +0.0000%。
- All-to-All / shared：平均 FCT +0.0000%，P99 slowdown +0.0000%，跨度 +0.0000%，队列 +0.0000%。
- All-to-All / joint32：平均 FCT +0.0000%，P99 slowdown +0.0000%，跨度 +0.0000%，队列 +0.0000%。
- Ring / shared：平均 FCT +0.0000%，P99 slowdown +0.0000%，跨度 +0.0000%，队列 +0.0000%。
- Ring / joint32：平均 FCT +0.0000%，P99 slowdown +0.0000%，跨度 +0.0000%，队列 +0.0000%。
- Fairness / shared：平均 FCT +0.0000%，P99 slowdown +0.0000%，跨度 +0.0000%，队列 +0.0000%。
- Fabric / shared：平均 FCT +0.0000%，P99 slowdown +0.0000%，跨度 +0.0000%，队列 +0.0000%。
- Receiver / shared：平均 FCT +0.0000%，P99 slowdown +0.0000%，跨度 +0.0000%，队列 +0.0000%。
- Hybrid / shared：平均 FCT +0.0000%，P99 slowdown +0.0000%，跨度 +0.0000%，队列 +0.0000%。

原大小区间、均值与 P95/P99/P99.9 均保留，图见 storage_bins.pdf；跨场景变化见 rescue_regression.pdf。无干预配对另逐字节核对 FCT 和所有汇总指标，不把四舍五入的零当成统计持平。

## 数据核验与剩余目标

三个关闭新选项的 GUARD 控制及四个基线与前轮逐流 FCT、全部指标一致。诊断开关配对也一致，日志有 1280 个匹配的完成事件，行数上限遗漏 0，观察到超时 0 次。该日志实际 ACK 数为 4001280，序列化 ACK 字节为 376120320，含包头、不含 IFG。

源码冻结在 guard-ackrescue，完整修改与实际测试可复查。analysis.json、comparison.json、diagnostic_analysis.json、validation_checks.json、raw_index.json 保存数据、干预计数、日志与哈希验证；每轮同时保存驱动脚本副本。

全部原图的统一配置优势尚未得到证明。Storage 大消息、Web/Analytics、完整 DP2 长尾与低队列的冲突、All-to-All、组件消融及补图仍需继续处理。此次十场景回归用于判断新修改是否增加退化，不能代替各场景对四个基线的独立确认。论文图片和文字需要等完整证据成立后更新。

## 当前统一配置与四基线的同构建复核

补充测量十个非 DP2 原场景的四个基线共 40 次。下列固定使用 Shared rescue 配置，并按指标比较本场景中最低的基线实测值；这是开发样本比较，不能证明统计优势。公平性、Ring 和消融等原图还包含其他专门指标，下面四项汇总不能代替这些完整图的验收。

- Storage30：Worst-port mean queue 高 134.49%（HPCC）。
- Storage50：Mean FCT 高 13.86%（Homa）；P99 slowdown 高 8.79%（Homa）；Trace span 高 5.77%（Homa）；Worst-port mean queue 高 149.45%（HPCC）。
- Web：Mean FCT 高 15.42%（Homa）；P99 slowdown 高 25.61%（Homa）；Worst-port mean queue 高 436.95%（HPCC）。
- Analytics：Mean FCT 高 1.20%（Homa）；Trace span 高 4.17%（Homa）。
- Fabric：Mean FCT 高 3.27%（HPCC）；P99 slowdown 高 1.48%（Homa）；Trace span 高 1.48%（Homa）；Worst-port mean queue 高 1925.06%（HPCC）。
- Receiver：这四项汇总的实测值均不高于四基线；仍需独立确认及原图专门指标核验。
- Hybrid：Worst-port mean queue 高 570.21%（HPCC）。
- Fairness：Mean FCT 高 43.23%（Homa）；P99 slowdown 高 0.66%（Homa）；Worst-port mean queue 高 16760.26%（HPCC）。
- All-to-All：Mean FCT 高 13.20%（Homa）；P99 slowdown 高 13.68%（DCQCN）；Trace span 高 15.36%（DCQCN）；Worst-port mean queue 高 5974.86%（DCQCN）。
- DP2：P99 slowdown 高 86.92%（Homa）；Worst-port mean queue 高 5664.81%（HPCC）。
- Ring：Mean FCT 高 1.01%（Homa）。

图见 figures/current_baseline_gaps.pdf、storage_baselines.pdf、workload_baseline_cdfs.pdf。大小区间样本数完整保留；未删除 GUARD 落后的区间或交叉 CDF。数据来源 current_baseline_gaps.json。

## 公平性与 Ring 原图的专门指标

- GUARD：原 10–12 ms 公共区间 Jain 指数 1.000000；Ring 跨度 11.709459 ms，丢包 0，通用超时恢复 0。
- HPCC：原 10–12 ms 公共区间 Jain 指数 0.626264；Ring 跨度 12.279750 ms，丢包 0，通用超时恢复 0。
- Homa：原 10–12 ms 公共区间 Jain 指数 0.250000；Ring 跨度 12.185071 ms，丢包 0，通用超时恢复 0。
- DCQCN：原 10–12 ms 公共区间 Jain 指数 0.928869；Ring 跨度 35.426546 ms，丢包 556532，通用超时恢复 0。
- TIMELY：原 10–12 ms 公共区间 Jain 指数 0.995117；Ring 跨度 115.550788 ms，丢包 3089198，通用超时恢复 13。

Homa 的 Ring 原生 RESEND 为 840 次，独立于通用恢复计数。公平性沿用原 100 µs 栅格补零，并核对公共区间内四条流均未完成；没有用平均 FCT 替代公平性指标。图见 figures/original_fairness.pdf 与 original_ring.pdf，数据见 original_metrics.json。这些仍是开发样本，不是独立确认。

## Storage 平均 FCT 差距的来源

- ali30：总体平均 FCT 差值（GUARD−Homa）为 -0.013442 µs；主要正向分量为 256K–2M 字节区间（1505 条合格流，贡献 0.236020 µs）。
- ali50：总体平均 FCT 差值（GUARD−Homa）为 2.792521 µs；主要正向分量为 256K–2M 字节区间（2430 条合格流，贡献 3.146914 µs）。

这里按原 5 ms 预热规则保留全部合格流，逐区间计算总 FCT 差并除以合格流总数，所有区间之和严格等于总均值差；没有删去少数长流。该分解用于确定后续源码诊断对象，不单独证明控制机制的因果关系。图见 figures/storage_gap_contributions.pdf。

## Storage 大消息速率限制诊断

- ali30：完整日志覆盖 2983 条被大小条件选中的流，其中 1505 条符合原预热规则。逐流控制路径采样点比例再取平均：网络上限被选中 3.76%，接收上限被选中 69.12%，上限相等 27.12%。同时低于 100 Gb/s 线速且选中接收上限的比例为 39.92%，选中网络上限的比例为 3.76%。
- ali50：完整日志覆盖 4882 条被大小条件选中的流，其中 2430 条符合原预热规则。逐流控制路径采样点比例再取平均：网络上限被选中 4.06%，接收上限被选中 86.46%，上限相等 9.47%。同时低于 100 Gb/s 线速且选中接收上限的比例为 76.01%，选中网络上限的比例为 4.06%。

日志过滤仅选择原始消息大小大于 256,000 字节的记录，实际流量和全部完成记录保持完整；新构建的无日志控制与上一构建以及同构建日志运行逐流 FCT、全部指标一致。全部被选择流均有匹配完成事件，没有行数上限遗漏。采样点比例不能解释为精确时间占比，路径选择标签沿用实际控制函数对尾部旁路的处理；选中接收上限不一定代表接收上限低于线速。这些记录不能单独证明全部延迟差距的因果来源。图见 figures/storage_cap_diagnosis.pdf。
