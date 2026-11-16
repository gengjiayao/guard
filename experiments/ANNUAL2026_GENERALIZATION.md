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

## Sender-aware receiver budgets

Probe4 (12 completed runs) confirms that grant-bounded release eliminates the
observed AliStorage pathological drain: makespan 78,719.271 -> 25,863.512 us.
Its overall P99 is 782.44 us versus Homa 928.62 us in that build; this is still
a development result. WebSearch remains regressed with K=2. Per-flow equal
grants yield 30,734.99 us versus Homa 34,031.34 us, insufficient margin.

Probe5 (8 completed runs; same runtime and trace hashes as probe4) tests bounded
byte-based pacing credit. Equal grants with 0.25 BDP credit yield WebSearch P99
30,551.47 us, but AliStorage P99 1,416.39 us. K=2 with the same credit yields
AliStorage 766.49 us but WebSearch 46,484.38 us. Thus no common fixed profile has
met the objective. All negative results remain in the result directories.

Lifecycle evidence at WebSearch trace times 20/40/60 ms shows respectively
101/149/219 registered messages but only 90/118/150 distinct sender-receiver
pairs (maximum 3/4/4 messages per pair). Equal allocation per message can reserve
multiple budgets from the same physical sender while its local SRPT scheduler
serves only one at a time.

`GuardSenderFairShare` allocates the residual capacity equally across distinct
senders. Within each sender, the shortest remaining received-byte work receives
that budget; other messages retain their configured minimum floor. Total
receiver capacity is unchanged. `GuardFairMixThresholdBdps` instead blends this
allocation with the existing K-limited bounded-work allocation when median
remaining active work grows from the configured threshold to twice it. The
median excludes domination by a single long outlier; the continuous transition
avoids a hard mode switch. It uses no CDF label or future information. Both
options default off, are mutually exclusive, and use ordinary direct grants.

Native tests exercise per-sender selection, progress-based promotion, unchanged
other-peer budgets, adaptive endpoints, capacity conservation and insertion
order independence. Probe6 tests unconditional and adaptive sender fairness,
with and without the bounded byte-credit change; old corrected GUARD and native
Homa are rerun in the same binary for comparison.

## Stable admission class and load generalization

Probe6 completed 16 runs. Sender-aware allocation improved WebSearch development
P99 by 12.91% (adaptive 16 BDP) to 17.26% (unconditional, byte credit), but the
corresponding AliStorage cases failed the joint target. Adaptive 32 BDP retained
AliStorage's 16.08% gain but yielded only 3.66% on WebSearch. Therefore the joint
objective remains unproven and no report result is replaced with these values.

`GuardFairMixOriginalSize` optionally uses the message size supplied at
registration for admission classification. Service order within each sender
continues to follow current receiver progress. This prevents a cohort of large
messages from being reclassified merely as its members drain; both behaviors
remain explicit and testable, with no traffic-label branching. Defaults remain
unchanged. A native regression checks stable versus progress-based admission.

Probe7 uses development input 6102 at both 50% and 80% host load. It compares
remaining-work and admission-size classification, K=1 versus K=2, and bounded
byte credit. Collective-specific duplex/cohort/burst options are disabled in
all candidate profiles. Homa is rerun with this frozen binary and identical
input. This remains development; the reserved final inputs are still untouched.

## Passive medium-message path

Probe7 completed 32 runs at input 6102. WebSearch 50% gains ranged 15.34--22.19%,
but WebSearch 80% gains remained 0.13--8.63%. AliStorage 50% gains remained
3.08--5.96%; only conservative admission-size policies retained >10% gains at
80%. This disproves generalization of the attractive 6101 results. No final
input has been used and no claim of joint success is justified.

`GuardRegistrationThresholdBdps` preserves the default one-BDP behavior at 1.
Larger values let multi-RTT messages up to the threshold use the existing HPCC
feedback path without receiver-set registration. They retain ALL hop telemetry,
use the unscaled passive utilization target, and cannot activate the grant-only
tail bypass. The one-BDP transport safety window, cumulative ACK/recovery,
physical rates and queue mappings are unchanged. Larger messages retain both
receiver grants and passive shared-fabric feedback. This tests whether frequent
medium-message membership changes unnecessarily delay the active service set.

Native admission tests verify exact class boundaries, default compatibility,
disjoint classes and the prohibition on bypassing passive feedback without
receiver authority. Existing controller invariant tests also pass. Probe8
compares thresholds of 2/4/8 BDPs, with fixed and adaptive sender-aware service,
against the previous admission policy and Homa on the same 6102 inputs at
50%/80%. All runs, regressions and failures remain available.

## Post-grant transport window

Probe8 completed 24 runs. Enlarging the passive admission range did not solve
the joint target and is not selected; the ordinary one-BDP registration boundary
remains the candidate default. All regressions, including larger AliStorage
tails for 4/8-BDP passive admission, are retained.

Queue summaries show p99 queue occupancy of 288,850 bytes (Ali50) and 425,100
bytes (Web80) for the preceding orig32 profile. At 100 Gb/s these queues can add
23--34 us at a busy link, exceeding the unloaded 4.16/8.32-us path RTT used by
the original fixed transport window. This motivates testing whether that
safety window leaves granted service unused while acknowledgments are delayed;
it does not by itself prove the bottleneck.

`GuardPostGrantWindowBdps` defaults to 1. A larger configured bound is applied
ONLY after an actual receiver grant passes the existing validity checks. The
initial ungranted window remains one BDP. Both pacing caps, physical rates and
reliability behavior remain unchanged; passive messages are excluded. The
expanded window cannot exceed the configured 2/4-BDP test limit or useful flow
size. The NIC is awakened if it was waiting solely for window credit.

Native tests verify unchanged initial flight, grant authority, bounded in-flight
bytes, unchanged rate caps, idempotence, first-grant barrier behavior, and passive
exclusion. Probe9 tests this control-window change with bounded-work, sender-fair
and adaptive allocation at 50%/80% load on development input 6102. Homa is rerun
with the same frozen runtime. Overall P99 remains the acceptance metric.

## Full-path feedback with bounded grant headroom

Probe9 completed 32 runs. On development input 6102, orig32 with a post-grant
2-BDP window reduced AliStorage P99 by 10.44% at 50% and 16.90% at 80%; 4 BDP
produced 10.73% and 21.32%. WebSearch 80% remained below target, so this is not
joint success. All comparisons in that probe used its same-build Homa runs.

Homa's numerical results have varied across GUARD-only rebuilt runtimes despite
unchanged baseline algorithms. The exact cause is not yet isolated. To eliminate
this confound, original `/home/gengjiayao/ict/guard` remains at 6c438d7 with its
binary hashes verified identical to the earlier WebSearch formal campaign.
`generalize_frozen_baseline` runs development inputs 6101/6102 at 50/70/80% on
that fixed original runtime. Subsequent acceptance must use a fixed baseline
runtime and verified identical input hashes, rather than a favorable baseline
from a different rebuild. Do not merge or rebuild the original while it runs.

`GuardReceiverHeadroom` tests limited grant overcommit (1--2 times the allocation
budget) to let available senders use shares temporarily unused by busy peers.
No physical capacity changes. Every individual grant remains at most the NIC's
actual rate. Enabling headroom requires full last-hop INT, the unscaled 0.95
passive target, no grant-only tail bypass, and ordinary direct grants without
legacy reclaimers. Thus both active permissions and full-path passive feedback
continue to constrain actual send rates. Runtime assertions enforce the same
requirements as the runner. Default factor 1 preserves all prior behavior.

Native tests verify the unchanged default, per-NIC cap and bounded aggregate
permission budget. Probe10 compares headroom 1/1.25/1.5/2 and sender-aware
allocation against the preceding orig32win2 profile and same-build Homa; the
original fixed-runtime baseline remains authoritative for later acceptance.

## Persistent, priority-preserving receiver reclamation

Probe10 completed 28 runs. Grant headroom with continuously binding full-path
feedback did not meet the joint objective and is not selected. The fixed original
baseline campaign completed all 12 runs; in particular its WebSearch-L80 6102
P99 is 25,821.05 us, stricter than some rebuilt same-source Homa results. This
fixed runtime will be used for acceptance, with exact input hashes checked.

The legacy work-conserving implementation had two concrete defects: every
membership/progress redistribution reset all rate measurements and cancelled
its timer, while periodic updates could replace the ordinary priority allocation
with equal shares even without confirmed unused capacity. Both behaviors are
now corrected. The timer and per-flow measurements persist across redistributions.
Receiver utilization includes all DATA, including unregistered/released messages.
Only persistent underuse with stable grant observations creates a donor cap.
Previously confirmed donor shares stay positive and normal service returns when
the sender makes progress at the retained cap. Reclaimed capacity goes first to
the shortest eligible remaining work. With no confirmed donor or no recipient,
the original target vector is preserved exactly. Total permissions stay within
the original one-line-rate budget; no overcommit is used here.

Native tests cover no-evidence priority preservation, donor bounds, recipient
selection, service restoration, no-recipient fallback, capacity conservation and
insertion-order independence. Probe11 compares 16/32/64-us observation periods
and existing allocation policies at 50/80% on development input 6102. Its Homa
reference is `guard/experiments/results/generalize_frozen_baseline`, not a new
baseline rebuilt alongside GUARD. No final validation input has been consumed.

## Remaining-work service priority with explicit drain acknowledgments

Probe11 completed all 24 runs; probe12 all 28. Independent audits checked all
52 complete input identities, output hashes, raw overall P95/P99 values and
common experiment parameters against the frozen original Homa executable.
No common profile meets the acceptance target. At WebSearch L80/6102, reclaim32
achieved 25,116.63 us versus fixed Homa 25,821.05 us (2.73% reduction). A single
service queue reached 24,753.07 us, still insufficient, and significantly harmed
short-message latency. Lower fabric targets and adaptive target rollback did
not improve the difficult WebSearch case. All failed hypotheses remain saved.

The next optional controller component is `guard_dynamic_priority=1` (default
off). The sender computes the dyadic service class from remaining message bytes
and path BDP. Before any low-to-high priority transition, its final old-class
DATA packet requests a cumulative ACK using one DSCP control bit. New DATA
waits until that exact byte boundary is acknowledged; retransmissions below
the boundary remain eligible. Receiver ACK batching cannot suppress the drain
ACK. At most six promotions occur per message, without any future-arrival,
workload-name, CDF or percentile input.

The UDP priority group remains immutable for QP identity, grants, admission,
ECN and PFC. Service class is encoded separately using the existing DSCP class
field. GUARD's opt-in switch dequeue additionally honors the head packet's
immutable PFC group, rather than assuming the service queue is that group.
Control packets and frozen baseline executables are unchanged. The feature
excludes the separate initial-window-priority mode. It still obeys all sender
rate caps, receiver grants, byte windows, and actual NIC serialization.

Native behavioral checks cover wire encoding, cumulative ACK gating, lost-ACK
waiting, retransmission eligibility, monotone remaining-work promotion,
immutable identity, PFC blocking by original group, and disabled behavior.
The complete packet-level workload campaign must additionally verify message
completion, NACK/recovery/drop counts, and measured P95/P99 before acceptance.
