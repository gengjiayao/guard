# NS-3 RDMA 拥塞控制对比实验平台

本仓库基于 [ConWeave (SIGCOMM'23)](https://doi.org/10.1145/3603269.3604849) 的 NS-3 仿真器扩展而来，目标是 **在同一份仿真代码内对比多种 RDMA 拥塞控制 (CC) 算法**。

`guard` 分支已经把以下三种独立的 CC 实现整合到同一棵代码树里，可以通过 `--cc` 参数一键切换：

| `--cc`    | `cc_mode` | 算法                                                        |
| --------- | --------- | ----------------------------------------------------------- |
| `dcqcn`   | 1         | Mellanox 版 DCQCN（原仓库自带）                              |
| `hpcc`    | 3         | 原版 HPCC（in-network INT 反馈），无任何接收端干预          |
| `timely` | 7         | TIMELY（基于 RTT）                                          |
| `dctcp`   | 8         | DCTCP（原仓库自带）                                         |
| **`homa`**  | **10**    | Homa 风格的接收端 credit 调度器（per-packet pacing）        |
| **`guard`** | **11**    | HPCC + 接收端等分配额上限 + EWMA 主动配额释放                |

> "guard" 是本仓库提出的算法，目标是在保留 HPCC in-network 反馈的同时，在接收端再加一层基于活跃流数的等分配额上限 + 主动尾部释放，主要改善大流的尾延迟。

---

## 1. 三种重点算法的设计

### 1.1 HPCC（`cc_mode=3`，对照基线）

完全保持 HPCC 原始逻辑：交换机在数据包内附 INT (qlen / txBytes / ts)，接收端把 INT 透传回 ACK，发送端按公式更新速率。本分支没有对 HPCC 做任何修改，作为基线对照。

### 1.2 Guard（`cc_mode=11`，本分支提出的算法）

在 HPCC 之上叠加一层 **接收端驱动的速率配额 (rate grant)**：

1. **接收端速率请求**：当一条流的第一个数据包（带 `FlowStatTag::FLOW_START`）到达，且总流大小 > 1 BDP，接收端把它登记到本 NIC 的活跃流集合 `m_rate_flow_ctl_set`。
2. **等分配额**：接收端把 `线速 / 活跃流数 N` 作为速率上限，给集合内 *所有* 流广播一个 `0xFB` Rate Grant 包。这是个**基于当前活跃流数的静态等分**——只在流加入 / 退出集合时重算，且不做"剩余带宽再分配"，所以**不是严格意义上的 max-min fair**；只有在接收 NIC 是唯一瓶颈、所有发送端都能跑满 `线速/N` 时，它才与 max-min 分配等价。
3. **发送端处理**：发送端把 grant 速率写进 `qp->hp.m_grantRate`，最终发送速率取 `min(HPCC 算出的速率, m_grantRate)`，由新增的 `SyncHwRate()` 统一下发。也就是说 grant 只起**封顶**作用，"用满剩余容量"这件事仍由 HPCC 那一层负责。
4. **主动配额释放（Proactive Release）**：接收端用 EWMA（`β=0.125`）实时估算每条流的瞬时接收速率，当 *剩余字节* < `est_rate × baseRTT × γ`（`γ=1.0`）时，认为这条流的剩余流量已经全部在飞行中，主动把它从集合里移除并广播新一轮 grant。
5. **INT hop 截断**：guard 模式下，接收端在回 ACK 前 *删掉最后一跳的 INT 信息*——因为最后一跳（接收端 NIC）的拥塞已经由 RCC 直接接管了，HPCC 不需要再为这一跳算速率。

控制包用一个新的 IPv4 协议号 `0xFB`（与 ACK=0xFC、NACK=0xFD、CNP=0xFF 并列），交换机按最高优先级转发。

### 1.3 Homa Simple（`cc_mode=10`，移植对照算法的简易版）

经典的接收端驱动 credit 调度（[SIGCOMM'18 Homa](https://dl.acm.org/doi/10.1145/3230543.3230564)）：

1. **HomaSimpleHeader**：每条流第一个数据包带额外字段 `bdp / homa_request / homa_unscheduled`，告诉接收端流的大小和初始 unscheduled 字节数（≈1 BDP 免 grant 的初始 burst）。
2. **HomaSimpleScheduler**：接收端为每个 NIC 维护一个 `HomaSimplePriorityQueue`（自实现二叉堆 + map）+ `wait_flow` 集合，按 `(pg, 剩余字节升序)` 即 **SRPT** 排序。
3. **Per-packet credit**：调度器周期性 pop 出最高优先级流，发一个 `0xFB` Homa Simple Credit 包，发送端每收到一个 credit 才能多发一个 MTU。
4. **状态切换**：流要么 `ACTIVE`（可拿 credit）要么 `WAITING`（已发出去的 credit 还没消化完），`ReceiveHomaSimpleData` 在每个 MTU 到达时按 token bucket 状态决定切换。

`0xFB` 包在 guard 和 homa-simple 模式下语义不同（grant 速率 vs. credit 颗粒），由 `RdmaHw::Receive()` 根据 `m_cc_mode` 分发。

> **⚠️ 当前 homa-simple 实现需配 `--pfc 1`（lossless）使用。** 第一个数据包携带 `HomaSimpleHeader`，丢失后接收端拿不到流大小信息、永远不下发 credit；发送端在用完初始 unscheduled credit 之后会停摆。要在 `--irn 1` 下使用需要补上请求包重发逻辑。

---

## 2. 关键文件

```
src/point-to-point/model/
├── rdma-hw.{h,cc}          # 三种算法的 RdmaHw 主体逻辑：ReceiveUdp 分支、UpdateRateHp、HomaSimpleScheduler、SyncHwRate
├── rdma-queue-pair.{h,cc}  # QP 结构：hp.m_grantRate（guard）、homa_simple.{is_request_package,m_credit_package,...}
├── homa-simple-header.{h,cc}  # Homa Simple 首包 header：homa_simple_bdp / homa_simple_requset / homa_simple_unscheduled
├── flow-stat-tag.{h,cc}    # 在 packet tag 里透传 baseRTT，给 guard 的 EWMA 阈值使用
└── switch-node.cc          # 0xFB 走 ECMP + 高优先级队列

src/network/utils/
├── custom-header.{h,cc}    # 反序列化时按 IntHeader::mode 解析 Homa Simple 字段；接受 0xFB 协议号
└── int-header.h            # IntHeader::mode：0=INT (HPCC/Guard) / 1=TS (Timely) / 2=Homa Simple / 5=none

src/internet/model/
└── seq-ts-header.{h,cc}    # 在 mode==2 时多塞一个 m_is_request 字段

src/point-to-point/model/qbb-net-device.cc
                            # 发送侧：mode==2 (homa) 时无 credit 不发包

scratch/network-load-balance.cc
                            # cc_mode → IntHeader::mode 映射；BW / qlen / flow-bw 监控

run.py                      # 入口脚本：cc_modes 字典、配置模板、调度仿真+分析
```

---

## 3. 编译

`waf 1.7.11` 是 ns-3.19 自带的，**只能用 Python 2** 引导（脚本里嵌了 bz2 二进制 archive，Python 3 无法解析含空字节的源码）。Debian 13 / Ubuntu 22.04+ 默认没有 Python 2，需要用 pyenv 装一个：

```bash
# 1. 安装 pyenv
curl -L https://pyenv.run | bash
export PYENV_ROOT="$HOME/.pyenv"
export PATH="$PYENV_ROOT/bin:$PATH"
eval "$(pyenv init - bash)"

# 2. 装 python 2.7.18 并锁定到当前仓库
pyenv install 2.7.18
cd /path/to/this/repo
pyenv local 2.7.18

# 3. 配置 + 编译
./waf configure --build-profile=optimized
./waf build
```

> 仿真本身、`run.py`、`fctAnalysis.py` 等运行时脚本仍然用 **Python 3**，只有 `./waf` 这个引导器需要 Python 2。

---

## 4. 跑仿真

```bash
python3 run.py --cc <hpcc|guard|homa|...> \
               --lb fecmp \
               --pfc 1 --irn 0 \
               --simul_time 0.01 \
               --netload 25 \
               --topo leaf_spine_8_100G_OS1
```

参数说明：

| 参数             | 含义                                        |
| ---------------- | ------------------------------------------- |
| `--cc`           | 拥塞控制算法（见上表），决定 `cc_mode`      |
| `--lb`           | 负载均衡：`fecmp/drill/conga/letflow/conweave` |
| `--pfc / --irn`  | 丢包恢复机制（恰好二选一）                  |
| `--simul_time`   | 仿真时长（秒），≥ 0.005                      |
| `--netload`      | 网卡负载百分比（25 表示 25%）                |
| `--topo`         | 拓扑名（见 `config/leaf_spine_*` 等）         |
| `--bw`           | 网卡带宽（Gbps，默认 100）                   |
| `--cdf`          | 流大小 CDF：默认 `AliStorage2019`，可选 `WebSearch` 等 |

每次仿真创建 `mix/output/<10位ID>/`，里面包含：

- `<id>_in.txt`：原始流输入
- `<id>_out_fct.txt` / `<id>_out_fct_summary.txt`：FCT 结果（slowdown 和绝对值的 P50/P95/P99/P99.9）
- `<id>_out_qlen.txt`：交换机出端口队列长度采样（每 1µs，guard 默认开）
- `<id>_out_bw.txt`：节点级吞吐采样（每 100µs）
- `<id>_flow_bw.txt`：每条流的吞吐采样
- `<id>_out_pfc.txt`：PFC 触发记录
- `config.txt` / `config.log`：本次仿真的输入配置和 stdout 输出

---

## 5. 内置拓扑

`config/` 下提供了多种 leaf-spine 拓扑（`leaf_spine_<N>_100G_OS<K>` 表示 N 个 host，oversubscription K:1）：

```
leaf_spine_8_100G_OS1     leaf_spine_8_100G_OS2     leaf_spine_8_100G_OS4
leaf_spine_12_100G_OS4
leaf_spine_16_100G_OS1    leaf_spine_16_100G_OS4
leaf_spine_64_100G_OS1
leaf_spine_128_100G_OS1   leaf_spine_128_100G_OS2
fat_k8_100G_OS2           # 3-tier
```

`netload` 必须能被 oversub 整除。

---

## 6. 流量发生器

`traffic_gen/traffic_gen.py` 在原版 Poisson 流之上加了可选的 incast 模式：

```bash
python3 traffic_gen/traffic_gen.py \
        -c traffic_gen/AliStorage2019.txt \
        -n 16 -l 0.25 -b 100G -t 0.01 \
        -i \                  # 启用 incast：仿真时间 20% 处 60→1 同时打 500KB
        -o config/L_25_..._flow.txt
```

`run.py` 会按 `(load, cdf, n_host, time, bw)` 自动构造文件名，已存在则跳过生成。

---

## 7. 验证（leaf_spine_8_100G_OS1, simul_time=0.01s, netload=25%, pfc=1）

| 模式  | <1BDP 平均/p99   | >1BDP 平均/p99   |
| ----- | ----------------| ----------------|
| hpcc  | 1.135 / 2.28    | 1.892 / 5.42    |
| guard | 1.131 / 2.22    | 1.817 / **3.68** |
| homa  | 1.190 / 3.43    | 1.667 / 3.88    |

数字是 FCT slowdown（实际 FCT / 理想 FCT）。guard 在大流尾延迟上比 vanilla HPCC 改进约 32%，符合"接收端公平分配 + 主动释放"的设计意图。

---

## 8. 致谢与许可

本仓库基于：

- [ConWeave (NUS, SIGCOMM'23)](https://github.com/conweave-project/conweave-ns3)
- [HPCC (Alibaba, SIGCOMM'19)](https://github.com/alibaba-edu/High-Precision-Congestion-Control)
- [TLT-RDMA (KAIST INA)](https://github.com/kaist-ina/ns3-tlt-rdma-public)

许可：MIT License。
