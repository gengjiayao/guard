# GUARD collective validation 2026

This experiment evaluates the complete ns-3 implementation, not a physical prototype.
The common simulator base is 20ebfe2f53fe9c1645ddf0d3b72325ef96f95a7f.
Development used seeds 1101 and 1102. Final seeds 1601 through 1605 are held out
until this configuration and the complete test matrix are committed.

## Frozen design

All four algorithms use identical flow files, dependency graphs, ECMP routing,
16 hosts, two leaf switches, four spine switches, 100 Gb/s links, 1 us propagation
per link, 9 MB switch buffers, and a physical 2:1 downlink/uplink ratio.
RDMA variants retain PFC and disable IRN. Homa retains its native authorization
and recovery implementation, with a 1 ms resend timeout. No baseline is slowed
or given different messages, routes, or dependencies to improve GUARD's result.

All-to-All sends to every other rank (256 KiB or 1 MiB per peer). All-to-Allv
preserves that per-rank total while assigning weight eight to one destination.
Ring AllReduce uses 16 ranks, 15 ReduceScatter steps and 15 AllGather steps,
with 1 MiB or 16 MiB tensors per rank. Every next step waits for both the local
previous send and its incoming previous-step transfer to complete. Two iterations
are separated by a full completion barrier. Concurrent jobs combine an 8 MiB
Ring AllReduce and 256 KiB-per-peer All-to-All, each with two iterations.
The model accounts for transport completion; it does not model GPU reduction
arithmetic, GPU execution or a complete training iteration.

Required mechanism cases are two-sender and seven-sender incast, mixed short/long
messages using AliStorage2019 with Poisson arrivals, and internal-link contention
with distinct receivers. Incast uses 2 MiB messages, eight rounds, 2 ms spacing,
and 0 to 0.5 us start jitter. The fabric case uses eight simultaneous cross-rack
flows to eight distinct receivers. Mixed traffic uses 10% host injection for
20 ms and excludes only flows starting in the first 5 ms, never slow completions.

The same GUARD profile is used in every case. It concentrates receiver credits
only when local outbound transfers are all acknowledged, keeps a 5% equal-share
floor, orders similar-sized contenders by receiver-relative peer order, and
bounds ACK batching by 1/16 path BDP (at least one and at most eight packets).
While the local NIC serves multiple outbound peers it retains eight-packet ACK
aggregation. These decisions read current local NIC state, not workload names,
future arrivals, remote simulator state, or the application's dependency graph.
The original proactive release remains enabled. Tail congestion gating and
adaptive fabric targets are development candidates, not enabled in this profile.

## Metrics and reporting

The primary measure is mean FCT for the four required mechanism cases, mean
per-iteration collective completion time (CCT) for the five individual collective
cases, and total makespan for the concurrent case. Two iterations are averaged
inside each seed; seeds, not flows or iterations, are the five independent
replicates. Report all five seeds, all completed flows and all failures.
Use paired per-seed percent reductions against each baseline; 95% t intervals
use four degrees of freedom. CCT is measured from first actual root start to
last terminal completion. Do not average heterogeneous concurrent job CCTs
as the primary concurrent performance metric.

Queue summaries run from 2.0 s until monitoring stops. The simulator stops after
all messages finish, so queue averages have algorithm-dependent horizons and
are diagnostic only. Do not label these averages as fixed-window comparisons.
Peak queues are sampled every 2 us and can miss sub-sample bursts. P99 FCT,
queues, control overhead and drops are separate metrics; a mean-FCT improvement
does not establish an improvement in all of them.

The report's main figures compare GUARD, HPCC, DCQCN and Homa. Original-config
GUARD regressions are retained separately for two incast cases; they are not
another algorithm in the report. No proactive-release-off arm is included.
Development attempts and less favorable sensitivity cases stay in the archive.

## Reproduction

Build with Python 2.7: `python waf configure --build-profile=optimized --disable-python --disable-tests`,
then `python waf build -j 6`. The historical ns-3 built-in core tests are not
enabled because of a pre-existing modern-compiler incompatibility. Dedicated
native packet/controller tests and workload/input integration tests are run.

Run `python3 experiments/annual2026_collectives.py --root experiments/results/annual2026_final_heldout --seeds 1601,1602,1603,1604,1605 --variants experiments/annual2026_final_variants.json`.
The runner freezes the git revision, binary hash, parameters and input hashes
before starting. Never rebuild or run another campaign in this worktree while
it is running. Resume only with the same plan. Use a new root for changed code.
Raw FCT identities and every DAG dependency edge are checked after every run.

Run `python3 experiments/analyze_collectives.py experiments/results/annual2026_final_heldout --output experiments/results/annual2026_final_analysis`.
For an extracted archive, pass its `raw` directory via `--raw-root`.
The analysis checks raw file hashes before producing tables. All generated
summaries use actual outputs; no manually entered performance numbers are used.

## Final results

The frozen 200 runs completed 295,424 flow records with every input identity and
DAG edge checked. Switch drops and RDMA timeout recoveries were zero. Homa
recorded seven native retransmissions; all messages completed. The four required
mechanism cases have lower mean FCT than each baseline. The primary results and
limitations are committed in experiments/reports/annual2026. The paired 95%
interval against Homa crosses zero for 1 MiB All-to-All; All-to-Allv and 1 MiB
Ring are not evidence of uniform superiority. All development outcomes are
preserved in the evidence archive.
