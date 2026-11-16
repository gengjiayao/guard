# P95 and P99 revision of the GUARD validation

This is a retrospective analysis of existing output, requested after the original
mean-FCT study. No new simulations or congestion-control tuning were performed
for this revision. The original plans, seeds, completion files and collective
completion-time figures remain unchanged. The report now uses P99 FCT as the
main flow-latency measure and P95 as a supporting measure.

## Statistical procedure

Recompute from raw flow completion records. Verify their stored SHA-256 hashes,
match every source/destination/size/start identity against the input, preserve
all completions and apply the original mixed-traffic warmup rule based only on
start time. The 80 required-case runs retain 150,732 analyzed flow records.

Quantiles use linear interpolation at (n-1)*q. Calculate each seed's quantile
before averaging the five seed statistics. Do not pool flows across seeds.
Paired improvements are 100*(1-GUARD/baseline) within each seed. Intervals use
a two-sided 95% t interval with four degrees of freedom across seed statistics.
These intervals are not confidence bounds for the population P99.

The directed cases have only 16, 56 and 64 completions per seed. Their empirical
P99 is near the sample maximum and is descriptive, not a robust estimate of
rare delays across changing traffic patterns. Mixed traffic has 7,275--7,566
analyzed completions per seed. Size strata are fixed at <=8 KiB, (8,64] KiB,
(64 KiB,1 MiB], and >1 MiB; the last two strata also have limited tail samples.
All four algorithms use exactly the same messages in every stratum.

## Findings

Against Homa, the P99 reductions are 1.952% for two-sender incast, 1.855% for
seven-sender incast and 0.917% for mixed traffic. The mixed-traffic paired 95%
interval includes zero. Fabric-contention P99 is 0.138% higher than Homa, with
an interval also including zero. GUARD's fabric P95 is higher than HPCC.

The previous 39.71% mean-FCT reduction versus original-config GUARD in
seven-sender incast does not carry over to P99: P99 increases by about 0.119%.
This is consistent with credit concentration completing some messages earlier
without materially shortening the last messages. Seven 2 MiB payloads require
at least 1,174.405 us to serialize through a 100 Gb/s receiver link, before
counting packet headers and propagation. Observed GUARD and Homa P99 values
are about 1,285.514 and 1,309.813 us respectively.

GUARD's aggregate CCT reductions versus Homa remain 7.49% for 256 KiB-per-peer
All-to-All, 1.75% for 1 MiB-per-peer All-to-All, 8.00% for 16 MiB-per-rank Ring
AllReduce and 8.69% for concurrent jobs. The 1 MiB All-to-All interval includes
zero. These are complete-configuration results, not proof of which component
caused the improvement.

## Why the current scenarios cannot establish large hybrid-control gains

Same-rack incast has no shared Spine path. Its actual reactive-binding rate
change count is zero. Mixed traffic injects only 10% host load, and <=8 KiB
messages have P99 around 9.172 us with GUARD versus 9.222 us with Homa.
The trace is dominated in message count by short transfers.

The frozen configuration enables one-RTT and tail bypass, uses an eight-BDP
tail threshold and disables the congestion gate. In rdma-hw.cc, GetNxtPacket
can latch tail bypass as soon as acknowledged remaining bytes fall under
this threshold. ReceiveAck skips HandleAckHp for a bypassed flow when the
gate is disabled; SyncHwRate uses the receiver grant cap while bypassing.
Thus some medium messages can bypass shared-fabric rate control from their
first packet. This is a configuration/code-path issue as well as a workload issue.

The stored counters show zero actual reactive-binding changes for 256 KiB
All-to-All, 1 MiB Ring and the tested concurrent jobs. Seven-sender incast and
these collective cases cannot by themselves demonstrate a benefit from the
interaction of active receiver control and reactive fabric control. The counter
table records both raw feedback-processing activity and actual rate bindings,
so receipt of telemetry is not confused with a control action.

## Next validation should use a tail-latency objective

Freeze P99 as the optimization objective and P95 as secondary before tuning.
Keep CCT/makespan as the collective objective. Expand samples and independent
traffic episodes, and always report per-size-bin counts. A practical target is
at least 10,000 observations per important size bin per seed; repeated copies
of an otherwise identical deterministic burst are not sufficient diversity.

Use multiple receivers sharing congested uplinks, short messages superposed on
collective background traffic, and changing receiver/fabric bottlenecks. Sweep
offered load and concurrency under identical inputs, routing, link rates and
buffer sizes for all algorithms. These tests are proposed, not completed.

Revisit the eight-BDP bypass condition and deferred-credit policy using P99,
not mean FCT, as the criterion. Verify that both control paths actually affect
rates in the intended mixed-bottleneck cases, then use controlled mechanism
experiments to establish causality. Do not promise a GUARD win before measuring.

The original Homa paper describes receiver-driven scheduling and identifies
core congestion as a limitation of its assumptions:
https://people.csail.mit.edu/alizadeh/papers/homa-sigcomm18.pdf (sections 3 and 6).
SIRD motivates the distinction between receiver-owned and shared links:
https://arxiv.org/abs/2312.15403 (abstract and design).
These sources motivate the follow-up design; their results are not GUARD data.

## Reproduction

In the experiment worktree:

    python3 experiments/analyze_tail_20261116.py experiments/results/annual2026_final_heldout --original-regression experiments/results/annual2026_original_regression --output experiments/results/annual2026_tail_review

For offline reanalysis, extract the earlier complete evidence ZIP and pass its
campaigns/annual2026_final_heldout directory, campaigns/annual2026_original_regression
directory and --raw-root pointing to its raw directory. The script uses only
the Python standard library and checks hashes before calculating values.
