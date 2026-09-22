# 流编号修复与接收端授权诊断

本轮 44 次原始负载开发实验全部记录，种子均为已经观察过的 301。总体目标仍未完成；本轮没有独立确认，也没有修改论文或 Overleaf。

## 修复的实现错误

FlowIDNUMTag 的编号成员为 32 位，但此前使用 U16 写入和读出，因此编号超过 65535 会回绕。标签声明的序列化长度仍为 8 字节，实际只写入 6 字节。已统一改成 U32 写入和读出，并初始化消息大小字段。真实 Packet 标签往返与拷贝测试在旧构建中复现 65536、65552、131088、2147483647 编号错误，新构建全部通过；标签仍占 8 字节，线上数据包长度不变。修改作用于共享模拟器，因此四个基线一起重测。

## 完整授权历史与核验

- Storage30：旧/新日志 110450 / 110432 行，分别覆盖全部 2983 / 2983 条被大小条件选中的流；原预热规则后 1505 条。无行数上限遗漏，授权发送和接收全部一一匹配。旧接收端编号用低 16 位、源/目的地址及原始大小唯一映射，修复后的编号直接与原始流号一致。
  修复前多发送方低授权（≤100 Mb/s）占合格大消息累计 FCT 的 9.73%，修复后 9.91%。这是授权状态区间，不等于实际瓶颈持续时间。
- Storage50：旧/新日志 361322 / 363020 行，分别覆盖全部 4882 / 4882 条被大小条件选中的流；原预热规则后 2430 条。无行数上限遗漏，授权发送和接收全部一一匹配。旧接收端编号用低 16 位、源/目的地址及原始大小唯一映射，修复后的编号直接与原始流号一致。
  修复前多发送方低授权（≤100 Mb/s）占合格大消息累计 FCT 的 21.34%，修复后 21.19%。这是授权状态区间，不等于实际瓶颈持续时间。

每种负载的日志开/关逐流 FCT 和全部汇总指标一致。旧源无日志结果还与上一轮完全一致。日志过滤仅影响记录，原始流量、完成记录和所有大小区间均保留。原配置的 work_conserving 实际为 0，不能把没有 demand 重分配记录误称为计时器失效。

## 修复后的性能影响

- Storage30 GUARD：均值 +0.1411%，P99 slowdown +0.6111%，最忙端口平均队列 +1.2897%；逐流 FCT 完全相同：False。
- Storage50 GUARD：均值 +0.0228%，P99 slowdown +0.9117%，最忙端口平均队列 -12.0364%；逐流 FCT 完全相同：False。
- Web GUARD：均值 +0.0000%，P99 slowdown +0.0000%，最忙端口平均队列 +0.0000%；逐流 FCT 完全相同：True。
- Analytics GUARD：均值 +0.0000%，P99 slowdown +0.0000%，最忙端口平均队列 +0.0000%；逐流 FCT 完全相同：True。

全部 20 个同协议前后比较、四基线实测值和原大小区间在 identity_comparison.json。图见 figures/identity_effects.pdf、grant_intervals.pdf、storage_fixed_baselines.pdf。

## 仍需处理

这次修复保证接收端排序使用完整编号，不预设它能改善所有性能。Storage 大消息的大部分授权受限区间出现在多发送方竞争时，单发送方限速区间占比很低；此前将共享授权扩展到短消息的方案导致 Ring 丢包，不能重复作为通用修复。下一步应检查多发送方服务宽度与实际可发送需求的匹配，并保留所有原场景回归、完整 DP2、消融及补图的要求。

## 统一 K=2 服务宽度实验

只把接收端并发服务数从 1 改成 2，所有场景使用相同配置；12-BDP 阈值及其他参数保持一致。以下均为开发样本。

- Storage30：Mean FCT -1.03%；P99 slowdown +0.00%；Trace span +0.05%；Worst-port mean queue +12.70%；丢包 0→0，超时 0→0。
- Storage50：Mean FCT -9.78%；P99 slowdown -7.97%；Trace span -1.83%；Worst-port mean queue +24.74%；丢包 0→0，超时 0→0。
- Web：Mean FCT -1.37%；P99 slowdown -1.26%；Trace span -0.98%；Worst-port mean queue +13.82%；丢包 0→0，超时 0→0。
- Analytics：Mean FCT +2.71%；P99 slowdown +11.66%；Trace span -2.63%；Worst-port mean queue +32.24%；丢包 0→0，超时 0→0。
- Fabric：Mean FCT +0.00%；P99 slowdown +0.00%；Trace span +0.00%；Worst-port mean queue +0.00%；丢包 0→0，超时 0→0。
- Receiver：Mean FCT +17.63%；P99 slowdown +0.64%；Trace span -0.00%；Worst-port mean queue +1909.91%；丢包 0→0，超时 0→0。
- Hybrid：Mean FCT +20.39%；P99 slowdown +2.15%；Trace span +1.79%；Worst-port mean queue +91.94%；丢包 0→0，超时 0→0。
- Fairness：Mean FCT +0.00%；P99 slowdown +0.00%；Trace span +0.00%；Worst-port mean queue +0.00%；丢包 0→0，超时 0→0。
- All-to-All：Mean FCT +0.00%；P99 slowdown +0.00%；Trace span +0.00%；Worst-port mean queue +0.00%；丢包 0→0，超时 0→0。
- Ring：Mean FCT +7.83%；P99 slowdown -1.80%；Trace span +5.18%；Worst-port mean queue +43.94%；丢包 0→0，超时 0→0。
- DP2：Mean FCT +0.00%；P99 slowdown +0.00%；Trace span +0.00%；Worst-port mean queue +0.00%；丢包 0→0，超时 0→0。

原公平性 Jain：K1 1.000000，K2 1.000000。Ring 按原图跨度、丢包与超时评估，不用额外均值指标替代。完整 DP2 保留所有 1280 条流及原固定队列观测窗口。逐流和所有大小区间数据仍保留；本轮结果不能替代四基线独立确认。

固定 K=2 不作为统一配置采用：Storage50 均值改善伴随队列增加，且 Analytics、Receiver、Hybrid 和 Ring 存在退化。保留 32 位编号修复，以 K=1 为后续对照；继续检查授权与实际可发送需求是否匹配，而不是按场景挑选 K。表述中的四舍五入零不构成统计持平结论，精确相同性另见 width_comparison.json。
