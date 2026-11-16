# Tail-first GUARD optimization, 2026-11-16

The requested target is more than 10% lower P99 flow completion time than Homa, preferably around 30%. This is an optimization target, not an assumed result. The earlier collective profile was selected on mean FCT/CCT and does not establish a P99 improvement.

## Workloads and comparisons

- Public empirical flow-size CDFs: HPCC's [AliStorage2019](https://github.com/alibaba-edu/High-Precision-Congestion-Control/blob/master/traffic_gen/AliStorage2019.txt) and [WebSearch](https://github.com/alibaba-edu/High-Precision-Congestion-Control/blob/master/traffic_gen/WebSearch_distribution.txt). The repository CDF values match these tables. Traffic is synthetic Poisson arrival traffic sampled from these empirical distributions; it is not a replay of production packet traces.
- Uniform non-self destinations, 16 hosts, 100 Gbit/s links, physical 2:1 leaf uplink oversubscription, ECMP, 9 MB buffers. Loads mean offered payload rate per host divided by host link capacity, not measured throughput or fabric utilization.
- Initial development uses seed 2101 and loads 20%, 50%, 70%. AliStorage2019 generates for 20 ms, WebSearch for 60 ms. The first 25% of the generation interval is a fixed start-time warmup. Every input flow, including warmup flows and the slowest flows, must complete and match the input identity. No completion-time truncation is permitted.
- Primary metric: per-seed overall P99 FCT. P95, fixed size bins, completion counts, drops/retransmissions, PFC and control activity are secondary. Never pool seeds for a claimed mean percentile. Improvements are paired by identical input snapshot.
- Homa keeps its native transport and automatically derives its priority profile from the same input snapshot. Physical resources and routing are shared across all arms. No baseline code changes are authorized as GUARD optimization.
- Initial holdout seeds 3101--3105 are reserved before tuning; if those results drive further tuning they become development evidence and a fresh holdout must be declared.
- All candidates and unsuccessful runs remain in the experiment archive. Freeze the winning control before running holdout. Report tested workload/load conditions and negative results alongside positive results; do not generalize one load point to all traffic.

## Mechanism hypothesis

The previous profile can enter tail bypass with eight BDPs still outstanding and then ignore reactive rate feedback. With a growing shared-link queue, the old gated implementation also used min(previous,current) queue length and revoked permission only on full RTT updates. The new implementation keeps HPCC's differential rate estimator but uses the current queue for GUARD's queue-budget policy, revoking permission on a fresh fast congestion sample. Safe fast ACKs cannot re-arm permission. Only full feedback rounds earn permission.

The test separates gating, queue-aware targets, a lower fixed target, a one-BDP tail, and tighter ACK cadence. This is a mechanism investigation: no candidate is declared successful before complete results and independent validation.
