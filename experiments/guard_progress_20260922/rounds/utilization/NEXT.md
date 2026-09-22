# Next bounded optimization step

Goal remains active. No final configuration meets all original figure metrics against HPCC, Homa, DCQCN and Timely. This round is observed seed 301 development, not independent confirmation.

Completed 65 simulations, none failed, all original traces complete, zero drops and generic RTO events. There are no live simulators. Source/build, original inputs/configs, frozen harness snapshots and every raw archive were hash-verified. Nine figures were visually inspected. No manuscript or Overleaf changes.

Sources: observation-only guard-utiltrace 8f9f6bc; optional RTT-window widening guard-utilwidth ef5d5a4; optional feedback gate guard-utilfeedback 1181dd9. All are separate clean worktrees, based on the shared full-width FlowID fix c2aedb0. Preserve original guard650811a and the user's two untracked artifacts directories. All optional policies remain default off; do not promote either widening policy as a final solution.

## What was established

Receiver DATA counters exactly conserve all input bytes and packets, including unregistered traffic. Grant interval analyses overlap across flows and must not be described as unique link-time fractions. Initial Storage high-grant interval receiver median is 78.01/62.23 Gb/s (30/50); low arrival alone does not imply spare end-to-end capacity. Sender grant-receipt snapshots are before pacing synchronization, not actual NIC selection events.

The ungated width rule only admits >=2 distinct senders with every active flow >12 path BDP and <=128 receiver BDP, one NIC. Two actual max-path-RTT windows below 70% DATA line rate promote K1 to K2; two above/equal85% demote. Progress grant refresh does not reset the RTT timer. Storage50 mean improves8.35%, P99slow5.60%, queue worsens2.42%; Hybrid mean+10.96%, queue+64.31%. Ring/Receiver/Fabric/Fairness/Alltoall/fullDP2 exact unchanged. Exact actual sampler validation: Ali30 7032 windows/433 promotions/225 demotions; Ali50 28187/1774/674; Hybrid310/1/1. Same-ns events can have distinct DATA totals; consecutive windows use exact previous sample counters, first windows require a unique compatible start counter among logged candidates (record this limitation).

The successor uses real serialized CAP_REPORT traffic and a new readiness bit in existing flags. Existing unused-in-report IRN32 carries the sender's received wire grant nonce; report-size and queue/link costs are real. With cap-report mode on, each legacy grant has an increasing per-flow nonce; receiver tracks first nonce of current >=90% grant epoch. A report must belong to that epoch, not be from a deferred-flow floor, claim >=90% final rate with no fabric binding, and have arrived within 2RTT. Sender readiness additionally requires actual full feedback >= high-grant start+RTT and at most one RTT old. Sender eligibility conservatively uses its own >12 and <=128 path-BDP size range, >=90% grant; reports at most once/RTT. This can suppress legitimate opportunities and is not optimal utilization. Legacy reliability/adaptive mode combinations rejected. Unit actual-wire round trip and stale/old/future nonce/low-grant/low-rate/negative report exclusions pass.

Three complete global profiles across all eleven scenes: K1, report-only K1, gated widening. Report-only effect retained separately. Every cross-source K1 control exact. Storage50/Hybrid observation reruns exact. Receiver-side replay verifies every window, membership, report -> prior sender grant-receipt ordering, report count, epoch/freshness gate, promotion, demotion and blocked count: Storage50 30228 windows,30106 received reports,1266 promotions,5856 blocked opportunities; Hybrid301 windows,338 reports,1 promotion,14 blocked. This is not a complete trace proof of every sender feedback-readiness event; source+wire unit provides that part of assurance.

Final gated profile relative K1:
- Storage30 mean-0.56%, P99slow-0.58%, span+0.17%, queue-6.21%.
- Storage50 mean-5.13%, P99slow-2.65%, span-0.85%, queue+10.50%.
- Web mean-5.30%, P99slow-6.58%, span+0.73%, queue-18.31%.
- Analytics mean-0.38%, P99slow+0.21%, span-0.30%, queue-1.32%.
- Fabric mean-0.94%, P99slow+2.27%, span+2.42%, queue-4.86% (same as report-only).
- Receiver mean+0.08%, P99slow+0.08%, span+0.08%, queue+7.21% (same as report-only; absolute queue~0.037→0.040us).
- Hybrid mean+7.78%, P99slow+0.53%, span+0.18%, queue+46.51%.
- Fairness,Alltoall,Ring,fullDP2 exact. Original Jain remains1.0 in10–12ms zero-filled100us grid. Ring11.709459ms0drops0RTO. FullDP2 1280flows80buckets,15.671423mean/85.400671P99/215.001914spanms and12.259150us worst queue, unchanged.

## Mechanism still unresolved

Ungated Hybrid width enters at2001811600ns with two active cross-rack flows to host5 and21.15Gb/s receiver arrival. Primary flow4 already fabric limited (~81→65Gb/s), halving its grant and enabling flow1 causes sustained oscillation/competition. Feedback gate initially blocks14 opportunities but enters at2001928080ns after report at2001923385ns for flow4 nonce168,99.9Gb/s. Last sampled full feedback2001919186ns showed fabric100Gb/s, stored u0.807; previous2001900945ns showed30.76Gb/s,u1.189. Positive feedback is real but transient; it does not establish stable free capacity. New width grants~48.417/51.582Gb/s. Demotion2003092880ns. No stale-token or validator bug explains the remaining regression.

Next hypothesis to test, not yet implemented: low receiver utilization should trigger widening only with evidence of sender NIC competition (e.g. another shorter ready flow/destination), in addition to appropriate fabric state. Hybrid has one original flow per sender so no such NIC competition; this is a mechanism-based condition, not a hard-coded scene exemption. This may also remove report overhead in single-flow Receiver/Fabric scenes. However Storage high-grant snapshots show only9.40% with shorter ready other-destination work, so gains may be limited. Instrument actual selection/service intervals before assuming this is the dominant cause. Alternatively study fabric-cap oscillation/stability while preserving all existing scope and counting real signaling costs. Do not simply tighten thresholds until this seed wins; prespecify, keep all outcomes and require independent all-baseline validation once a viable global candidate exists.

Do not repeat already rejected fixedK2, all-size adaptive targets, large windows, ACK deadline or earlier source candidate grids without new evidence. Earlier source/evidence history is in predecessor work/guard_grantdiag_20260921/STATE.md and other NEXT files. Full scope still includes original strict ablations, OFLM, flow bins and supplemental widths. No per-figure configuration switching, no shortened DP2, no metric replacements, no favorable-only plotting.
