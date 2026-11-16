# GUARD workload generalization development

Objective: reduce overall post-warmup P99 FCT versus unchanged native Homa by
more than 10% for both AliStorage2019 and WebSearch at 50%, 70%, and 80%
offered host load. P95 remains a secondary reported metric. Do not substitute
size bins, pool repeated-trial flows, censor unfinished transfers, or change
baseline configurations to reach the target.

Development traces: 6101, then 6102 as needed. Reserve 7101--7110 for final
validation of a frozen configuration. The inherited runner's legacy
`reserved_holdout_seeds` field refers to an older campaign; this document is
the allocation for this optimization round. All failures and regressions stay
in the campaign folders. Baselines, topology, traffic generation, physical
capacity, and routing are unchanged.

## Evidence before the new controller option

`experiments/results/generalize_probe1`: 16/16 completed. At 80% load (6101),
old GUARD P99 was 43,380.08 us versus Homa 33,435.79 us on WebSearch; AliStorage
was 749.59 us versus 949.05 us. Unbounded equal receiver grants improved
WebSearch to 30,387.65 us but regressed AliStorage to 1,234.28 us. Adding a
minimum-rate fraction or service-age protection did not solve both workloads.

`experiments/results/generalize_probe2`: 14 completed and two pre-simulation
configuration rejections. The attempted window floor was rejected because its
required transition-prefix barrier was disabled; no result is inferred from
those rejected runs. Legacy cap reclamation, periodic reclamation, and a lower
fabric target did not jointly improve both workloads. All original raw files,
commands, failures, and input/runtime hashes are retained.

## New bounded-work / long-flow receiver allocation

`GuardLongFlowThresholdBdps` defaults to zero and leaves existing behavior
unchanged. A nonzero value uses only remaining bytes observed at the receiver
and the registered path's BDP. When bounded remaining work exists, at most K
such messages receive the weighted residual capacity after minimum floors.
When all remaining messages exceed the threshold, all share capacity equally.
Thus the long-flow population is no longer always serialized behind K peers,
while bounded messages retain prompt completion. The existing passive fabric
cap, sender pacing, proactive lifecycle and reliability mechanisms remain.
No workload identity, CDF, future arrival, percentile, or global simulator
state enters the allocator. Different thresholds are development hypotheses,
not accepted performance claims.

Checks: optimized ns-3 build; standalone native tests with assertions enabled
for capacity conservation, deterministic allocation, progress-based promotion,
long-flow service restoration and disabled mode; existing
`tests/guard_collective_control.cc` invariants also pass. Test linking uses
`build` ns3.19 point-to-point/internet/network/core optimized libraries.

Campaign `generalize_probe3` compares 8, 16 and 32 BDP thresholds against the
unchanged old GUARD, equal-grant GUARD and Homa on identical 6101 traces.

## Grant-bounded proactive release

Probe3 completed all 12 runs. Pure bounded-work priority still trades WebSearch
against AliStorage; none is accepted as a final profile. The old GUARD and
equal-grant arms reproduced their P99 values from probe1. Homa WebSearch P99
was 34,031.01 us in this binary versus 33,435.79 us in the earlier binary;
therefore always rerun baselines with the frozen final runtime, rather than
reusing a favorable baseline from an older build.

`generalize_release_trace` completed two unchanged-GUARD runs with bounded
lifecycle/controller tracing. AliStorage flow 4688 was proactively released
with 763,317 bytes remaining, retained a 100 Mb/s grant, and took 65,930.416 us
after release to complete. Five further traced flows showed the same prolonged
low-grant tail. WebSearch had no traced post-release tail longer than 1 ms;
this defect is real, but does not explain the entire WebSearch regression.
Raw trace outputs: mix/output/322512021 (Ali), mix/output/765828437 (Web).

`GuardGrantBoundedRelease` bounds the release threshold by both measured
arrival rate and the last receiver-issued grant. An arrival burst from a prior
higher grant must not authorize removal of work requiring far more than gamma
RTTs at the retained cap. Disabled by default for controlled comparison.
The passive fabric cap may further limit actual delivery; the bound is a
necessary service-budget check, not a guarantee of tail completion time.
Native regression `tests/guard_release_bound.cc` checks the observed low-grant
case, monotonicity, rate bounds and invalid/zero input handling.

Probe4 compares the correction alone, equal grants, bounded-work grants and a
one-RTT release threshold against unchanged old GUARD and Homa. No acceptance
claim precedes measured overall P99 and later independent validation.
