# GUARD ACK 批次调度与 Homa 重复性

完整论文优势目标仍在进行中。本轮共 70 次仿真尝试，70 次完成，0 次失败。所有运行使用已经观察的开发种子 301；原始输入、预热、全部流和固定队列观察窗口保留。本轮没有进行新种子的独立确认，也没有将候选修改推广到论文。

## Homa 重发顺序

Homa 原先按指针哈希表的迭代顺序发送同时到期的 RESEND。仅改变哈希桶的内部表示，旧实现的完整 DP2 就产生三组不同 FCT；这不是协议参数变化。修复按消息 ID 和端点的固定顺序发送同一批到期重发，保持原定时器、重发范围、授权及优先级规则。

同一二进制的两次默认桶重复以及 11/257 桶两组检查，修复后的逐流 FCT 和全部汇总指标完全相同。另一个包含 GUARD 调度改动的构建也运行 Homa，用于检查跨构建一致性。全部旧结果仍在记录中，没有根据性能挑选桶或顺序。固定顺序的意义是消除容器表示对结果的影响，不能证明该仿真完整等同于其他 Homa 实现。

图见 figures/homa_order.pdf，精确一致性检查见 validation_checks.json。

## GUARD 调度修改

已有独立公平轮询每次服务一个包，可能让低优先级流长期停在不足八个包的 ACK 批次中。新选项保持原有最短流量子和一次公平发送的份额，在连续公平机会中优先补齐同一流当前批次。目标使用发送端累计确认序列加既有 ACK 间隔，开始后固定；补齐、流结束、索引身份变化或失去发送资格后，继续轮询其他流。

该修改默认关闭，要求开启独立公平游标，没有添加 ACK 定时器或修改 RTO。实际调度器测试验证配置的 64:1 份额、部分批次补齐、三名竞争者都得到服务，以及暂停、窗口、发送时间、完成、索引复用时不阻塞其他合格流。单元测试不替代下列完整性能测量。

## 完整 DP2

每次运行均为原始 1,280 条流、每主机 2 GB 的完整轨迹。三个父配置各做同构建配对，四个外部基线使用相同构建及输入。

- Shared cursor：平均 FCT 15.669 ms，P99 88.793 ms，跨度 216.534 ms，队列 12.478 µs，超时恢复 0，PFC 暂停 0。
- Shared batch：平均 FCT 16.072 ms，P99 93.676 ms，跨度 215.869 ms，队列 12.649 µs，超时恢复 1，PFC 暂停 0。
- Joint32 cursor：平均 FCT 16.450 ms，P99 58.835 ms，跨度 216.961 ms，队列 24.707 µs，超时恢复 0，PFC 暂停 26。
- Joint32 batch：平均 FCT 16.258 ms，P99 55.827 ms，跨度 216.624 ms，队列 26.944 µs，超时恢复 0，PFC 暂停 150。
- Shared λ1 cursor：平均 FCT 24.482 ms，P99 103.222 ms，跨度 227.558 ms，队列 5.313 µs，超时恢复 3，PFC 暂停 0。
- Shared λ1 batch：平均 FCT 24.389 ms，P99 100.024 ms，跨度 225.512 ms，队列 7.719 µs，超时恢复 4，PFC 暂停 0。
- Homa：平均 FCT 18.146 ms，P99 45.688 ms，跨度 230.976 ms，队列 53.810 µs，超时恢复 0，PFC 暂停 0。
- HPCC：平均 FCT 28.677 ms，P99 72.094 ms，跨度 226.362 ms，队列 0.213 µs，超时恢复 0，PFC 暂停 0。
- DCQCN：平均 FCT 25.343 ms，P99 77.993 ms，跨度 224.544 ms，队列 4.626 µs，超时恢复 0，PFC 暂停 0。
- TIMELY：平均 FCT 39.089 ms，P99 84.885 ms，跨度 240.235 ms，队列 16.592 µs，超时恢复 0，PFC 暂停 3873。

图见 figures/batch_controls.pdf、batch_baselines.pdf、batch_cdf.pdf、queue_ranks.pdf、batch_events.pdf。Homa 的通用 RTO 计数为零，但发生 10,618 次原生 RESEND，两类计数在图中分别呈现。CDF 和三个最繁忙端口的队列同时保留；均值改善不能覆盖尾延迟或队列退化。

## 跨场景回归

- Web / shared：平均 FCT -0.04%，P99 slowdown -0.44%，跨度 -0.10%，队列 +0.76%。
- Web / joint32：平均 FCT -0.05%，P99 slowdown +0.06%，跨度 -0.01%，队列 -0.17%。
- Analytics / shared：平均 FCT +0.01%，P99 slowdown +0.04%，跨度 -0.02%，队列 +0.32%。
- Analytics / joint32：平均 FCT +0.01%，P99 slowdown -0.59%，跨度 -0.01%，队列 -0.00%。
- All-to-All / shared：平均 FCT -0.31%，P99 slowdown -0.21%，跨度 +0.07%，队列 -3.50%。
- All-to-All / joint32：平均 FCT -0.13%，P99 slowdown +0.12%，跨度 +0.88%，队列 -4.50%。
- Ring / shared：平均 FCT +0.00%，P99 slowdown +0.00%，跨度 +0.00%，队列 +0.00%。
- Ring / joint32：平均 FCT +0.01%，P99 slowdown +1.03%，跨度 +0.05%，队列 -0.47%。
- Storage30 / shared：平均 FCT +0.11%，P99 slowdown -0.36%，跨度 -0.02%，队列 -2.26%。
- Storage50 / shared：平均 FCT -0.04%，P99 slowdown +2.69%，跨度 -2.57%，队列 -10.22%。

图见 figures/batch_regression.pdf 和 storage_bins.pdf。Storage 每个大小区间的样本数、均值及 P95/P99/P99.9 均保留在 analysis.json。所有百分比都是开发样本的实测变化，微小差别尚不能称为统计持平。

## 范围与证据

原论文所有负载、大小分组、网络/接收/混合拥塞、严格消融、OFLM、公平性、All-to-All、完整 DP2、Ring 及两组补图继续保留在验收范围。本轮覆盖六个跨场景配对和完整 DP2，并非全部原图的四基线确认。当前还没有一套统一配置在全部指标上达到用户要求。

每轮保存源码提交、二进制、拓扑、输入与驱动脚本哈希；原始输出归档见 raw_index.json。analysis.json、comparison.json、validation_checks.json 提供可复查数值及完整性验证。控制日志配对检查逐流 FCT 和全部指标一致，并逐项检查完成事件与截断数。源码隔离在 guard-homastable、guard-ackbatch 和 guard-servicebudget，原 guard 源码及用户数据保留。

## 累计发送配额修复

批次调度的完整结果仍有退化，进一步复现发现：两个短流交替满足发送条件时，旧“连续同一流 64 包”的规则永远不触发让步。实际调度器中，始终合格的第三个长流在 650 次发送中获得 0 次服务，分配为 325/325/0。累计所有优先发送包数后，在既有 64 包量子后执行一次公平发送；同一复现变为 320/320/10，在批次开关关闭和开启时均成立。

选项 guard_sender_service_budget 默认关闭，要求独立公平游标。实际测试同时保留单一最短流时的 64:1 份额、原批次补齐及资格排除测试。发送累计计数在流身份切换时保留，只在确实选择其他合格流后清零；没有其他合格流时继续服务，保持到期让步状态。

以下是新构建的完整 DP2 同版本配对；没有按场景选择不同的量子。

- Shared cursor：平均 FCT 15.669 ms，P99 88.793 ms，跨度 216.534 ms，队列 12.478 µs，超时恢复 0，PFC 0。
- Shared budget：平均 FCT 16.254 ms，P99 108.958 ms，跨度 216.197 ms，队列 13.050 µs，超时恢复 0，PFC 0。
- Shared budget + batch：平均 FCT 16.106 ms，P99 95.247 ms，跨度 215.888 ms，队列 12.732 µs，超时恢复 0，PFC 0。
- Joint32 cursor：平均 FCT 16.450 ms，P99 58.835 ms，跨度 216.961 ms，队列 24.707 µs，超时恢复 0，PFC 26。
- Joint32 budget：平均 FCT 16.357 ms，P99 56.172 ms，跨度 217.264 ms，队列 26.504 µs，超时恢复 0，PFC 0。
- Shared λ1 cursor：平均 FCT 24.482 ms，P99 103.222 ms，跨度 227.558 ms，队列 5.313 µs，超时恢复 3，PFC 0。
- Shared λ1 budget：平均 FCT 25.567 ms，P99 105.516 ms，跨度 226.814 ms，队列 2.470 µs，超时恢复 0，PFC 0。
- Shared λ1 budget + batch：平均 FCT 25.361 ms，P99 99.491 ms，跨度 226.012 ms，队列 2.403 µs，超时恢复 0，PFC 0。

新构建 Homa 与前一构建和全部固定重发顺序检查一致。三个关闭新选项的 GUARD DP2 控制也逐流一致。CDF 中 HPCC、DCQCN 和 TIMELY 明确标为前一构建参照，本次未重复它们，不能描述为新构建全基线确认。图见 figures/budget_controls.pdf、budget_cdf.pdf 和 budget_regression.pdf、budget_storage_bins.pdf。

- Web / shared：平均 FCT +0.17%，P99 slowdown +0.95%，跨度 +0.04%，队列 -4.92%。
- Web / joint32：平均 FCT -0.27%，P99 slowdown -0.62%，跨度 +0.00%，队列 -0.76%。
- Analytics / shared：平均 FCT +0.35%，P99 slowdown +2.03%，跨度 +0.05%，队列 -1.27%。
- Analytics / joint32：平均 FCT +0.21%，P99 slowdown -0.02%，跨度 +0.03%，队列 -0.80%。
- All-to-All / shared：平均 FCT +4.82%，P99 slowdown -0.12%，跨度 +1.35%，队列 +12.97%。
- All-to-All / joint32：平均 FCT +4.91%，P99 slowdown +0.51%，跨度 +0.35%，队列 +12.20%。
- Ring / shared：平均 FCT -2.64%，P99 slowdown -5.82%，跨度 -1.37%，队列 -1.74%。
- Ring / joint32：平均 FCT +0.99%，P99 slowdown +3.45%，跨度 +0.40%，队列 -0.37%。
- Storage30 / shared：平均 FCT +0.37%，P99 slowdown +0.02%，跨度 -0.01%，队列 +1.51%。
- Storage50 / shared：平均 FCT -0.08%，P99 slowdown +0.38%，跨度 -1.95%，队列 -15.16%。

## 完整诊断日志

- Shared λ1 / cursor：3 次超时，在途字节依次为 [4000, 7000, 3000]；ACK 4001280 个，序列化 ACK 字节 376120320。
- Shared λ1 / batch：4 次超时，在途字节依次为 [4000, 7000, 4000, 2000]；ACK 4001280 个，序列化 ACK 字节 376120320。
- Shared λ1 / budget：0 次超时，在途字节依次为 []；ACK 4001280 个，序列化 ACK 字节 376120320。

三组日志配对均核对逐流 FCT 和全部指标一致，完成事件各 1,280 个，无达到上限而遗漏的事件。字节数含包头、不含 IFG。修复调度缺陷不等于已实现所有原图全面优势；新种子确认、全实验统一配置和论文更新仍未完成。
