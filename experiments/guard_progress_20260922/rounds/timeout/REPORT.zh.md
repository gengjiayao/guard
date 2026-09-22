# GUARD ACK 等待、空闲超时与发送轮询实验

完整论文优势目标仍在进行中。本轮共记录 90 次运行尝试，75 次完整仿真，15 次配置或实现失败均保留。全部使用已经观察的开发种子 301，尚未独立确认，也没有推广到 Overleaf。

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

- Shared：平均 FCT 15.932 ms，P99 93.682 ms，跨度 216.361 ms，队列 12.411 µs，超时恢复 0，PFC 暂停 0。
- Shared + deadline：平均 FCT 17.316 ms，P99 79.685 ms，跨度 217.204 ms，队列 25.085 µs，超时恢复 0，PFC 暂停 0。
- Joint32：平均 FCT 16.454 ms，P99 57.846 ms，跨度 217.394 ms，队列 26.051 µs，超时恢复 0，PFC 暂停 2。
- Joint32 + deadline：平均 FCT 15.643 ms，P99 48.639 ms，跨度 216.870 ms，队列 37.925 µs，超时恢复 0，PFC 暂停 7460。
- Homa：平均 FCT 17.733 ms，P99 51.224 ms，跨度 230.130 ms，队列 56.067 µs，超时恢复 0，PFC 暂停 0。
- HPCC：平均 FCT 28.677 ms，P99 72.094 ms，跨度 226.362 ms，队列 0.213 µs，超时恢复 0，PFC 暂停 0。
- DCQCN：平均 FCT 25.343 ms，P99 77.993 ms，跨度 224.544 ms，队列 4.626 µs，超时恢复 0，PFC 暂停 0。
- TIMELY：平均 FCT 39.089 ms，P99 84.885 ms，跨度 240.235 ms，队列 16.592 µs，超时恢复 0，PFC 暂停 3873。

Joint32 加 ACK 等待上限虽然降低了平均和 P99 FCT，却触发 7,460 次 PFC 暂停，队列也增大；不能作为全面优势的结论。Homa 在不同源码构建中的结果仍有波动，此处仅使用本次同版本测量；后续还需检查其重发扫描顺序的确定性。

完整分布见 figures/deadline_cdf.pdf；均值、尾部、跨度和队列同时保留，不能只选择改善的指标。

## 低增益与空闲定时器修复

- bounded_shared_l10（Shared λ1）：平均 FCT 24.295 ms，P99 99.605 ms，跨度 226.015 ms，队列 3.530 µs，超时恢复 2，PFC 暂停 0。
- bounded_shared_l10_deadline（Shared λ1 + deadline）：平均 FCT 29.795 ms，P99 102.276 ms，跨度 232.329 ms，队列 8.268 µs，超时恢复 0，PFC 暂停 0。
- bounded_joint32_l10（Joint32 λ1）：平均 FCT 21.937 ms，P99 70.141 ms，跨度 230.575 ms，队列 2.706 µs，超时恢复 16，PFC 暂停 0。
- bounded_joint32_l10_deadline（Joint32 λ1 + deadline）：平均 FCT 25.742 ms，P99 65.431 ms，跨度 230.724 ms，队列 13.716 µs，超时恢复 0，PFC 暂停 0。
- idle_shared_l10（Shared λ1 + idle fix）：平均 FCT 24.295 ms，P99 99.605 ms，跨度 226.015 ms，队列 3.530 µs，超时恢复 2，PFC 暂停 0。
- idle_shared_l10_deadline（Shared λ1 + both fixes）：平均 FCT 29.795 ms，P99 102.276 ms，跨度 232.329 ms，队列 8.268 µs，超时恢复 0，PFC 暂停 0。
- idle_joint32_l10（Joint32 λ1 + idle fix）：平均 FCT 21.937 ms，P99 70.141 ms，跨度 230.575 ms，队列 2.706 µs，超时恢复 15，PFC 暂停 0。
- idle_joint32_l10_deadline（Joint32 λ1 + both fixes）：平均 FCT 25.742 ms，P99 65.431 ms，跨度 230.724 ms，队列 13.716 µs，超时恢复 0，PFC 暂停 0。

## 独立轮询游标的同版本配对

- cursor_shared（Shared）：平均 FCT 15.932 ms，P99 93.682 ms，跨度 216.361 ms，队列 12.411 µs，超时恢复 0，PFC 暂停 0。
- cursor_shared_cursor（Shared + cursor）：平均 FCT 15.669 ms，P99 88.793 ms，跨度 216.534 ms，队列 12.478 µs，超时恢复 0，PFC 暂停 0。
- cursor_joint32（Joint32）：平均 FCT 16.454 ms，P99 57.846 ms，跨度 217.394 ms，队列 26.051 µs，超时恢复 0，PFC 暂停 2。
- cursor_joint32_cursor（Joint32 + cursor）：平均 FCT 16.450 ms，P99 58.835 ms，跨度 216.961 ms，队列 24.707 µs，超时恢复 0，PFC 暂停 26。
- cursor_joint32_l10_deadline（Joint32 λ1 + deadline）：平均 FCT 25.742 ms，P99 65.431 ms，跨度 230.724 ms，队列 13.716 µs，超时恢复 0，PFC 暂停 0。
- cursor_joint32_l10_deadline_cursor（Joint32 λ1 + deadline + cursor）：平均 FCT 25.730 ms，P99 66.193 ms，跨度 230.863 ms，队列 14.705 µs，超时恢复 0，PFC 暂停 0。

游标版本完成了 Web、Analytics、All-to-All、Ring 的两组同版本配对回归，尚未完成十个原始场景及四基线的全套独立复测，因此不能借用前一个版本的结果宣称新版本全面领先。图见 figures/cursor_controls.pdf 和 cursor_regression.pdf。单元测试证明轮询缺陷得到修复，不能代替真实性能验证。

- web40 / shared 加游标：平均 FCT -0.11%，P99 slowdown +0.65%，跨度 +0.01%，队列 +0.53%。
- web40 / joint32 加游标：平均 FCT +0.16%，P99 slowdown -0.71%，跨度 +0.01%，队列 +1.12%。
- fb40 / shared 加游标：平均 FCT -0.07%，P99 slowdown +0.14%，跨度 -0.01%，队列 -0.21%。
- fb40 / joint32 加游标：平均 FCT +0.05%，P99 slowdown +2.27%，跨度 +0.01%，队列 -0.46%。
- alltoall / shared 加游标：平均 FCT +0.43%，P99 slowdown +0.92%，跨度 -0.28%，队列 +1.81%。
- alltoall / joint32 加游标：平均 FCT +0.18%，P99 slowdown -0.56%，跨度 -0.68%，队列 +5.32%。
- ring / shared 加游标：平均 FCT +0.97%，P99 slowdown +9.55%，跨度 -2.99%，队列 +1.25%。
- ring / joint32 加游标：平均 FCT +0.02%，P99 slowdown -0.18%，跨度 -0.15%，队列 -0.10%。


## ACK 等待上限的十场景回归

以下是同版本 Shared 的变化，正数表示退化；完整图见 figures/deadline_regression.pdf。

- Storage30：平均 FCT -0.20%，P99 slowdown -0.56%，跨度 -0.05%，队列 +9.34%。
- Storage50：平均 FCT -0.72%，P99 slowdown +0.24%，跨度 -1.90%，队列 +3.50%。
- Web：平均 FCT -0.14%，P99 slowdown -0.39%，跨度 +0.01%，队列 -0.30%。
- Analytics：平均 FCT -0.06%，P99 slowdown +0.04%，跨度 -0.01%，队列 +0.54%。
- All-to-All：平均 FCT +0.29%，P99 slowdown +0.86%，跨度 +0.86%，队列 -0.19%。
- Ring：平均 FCT +1.93%，P99 slowdown -2.00%，跨度 -3.77%，队列 +78.69%。
- Fairness：平均 FCT +0.00%，P99 slowdown -0.00%，跨度 -0.00%，队列 +0.00%。
- Fabric：平均 FCT -0.02%，P99 slowdown -0.00%，跨度 +0.00%，队列 -0.05%。
- Receiver：平均 FCT -0.00%，P99 slowdown -0.00%，跨度 -0.00%，队列 +0.07%。
- Hybrid：平均 FCT -0.40%，P99 slowdown -0.34%，跨度 -0.34%，队列 -0.89%。

## 证据与剩余范围

所有配置生成失败、崩溃、截断日志及补跑分别保留，没有覆盖或挑选成功运行。最初启动还因缺失 runs 目录提前失败，记录在 bootstrap-failed.log；此时尚未产生单项运行记录。分析入口为 analysis.json、diagnostic_analysis.json、comparison.json、validation_checks.json、raw_index.json；每轮保存当时的完整驱动脚本副本。

下一步围绕实际轮询修复与网络反馈的交互继续优化，处理队列与尾延迟的取舍。原论文所有负载、大小分组、网络/接收/混合拥塞、严格消融、OFLM、公平性、All-to-All、完整 DP2、Ring 及两组补图仍需统一配置和四基线复测。独立种子确认与论文文字、图片更新尚未完成。
