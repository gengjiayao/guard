# Receiver grant diagnosis

Previous turn made progress: 83 completed verified runs and conditional ACK rescue evidence. Full all-original-figure objective remains active. No paper promotion or independent seed reuse as confirmation.

Run original full Storage30 and Storage50 seed301 with the fixed Shared rescue candidate, grant observations off/on (four runs). No traffic filter or configuration optimization in this first round. Observation-only source appends original flow size, sender count, flows sharing source NIC, minimum remaining work, receiver sequence and total remaining work to selected grant events. Select original size >256000 bytes, preserve all eligible original traffic/FCT and all bins. Cap 1000000 records; any cap omissions must be reported, never treated as full coverage. Unknown retired ACKs have no recoverable size and are explicitly filtered when minimum size is positive.

Require exact complete FCT/metrics across paired runs and preceding frozen source, hash checks and matched grant send/receive records. Determine whether large flows encounter single-sender duplicate serialization, weighted contention, deferred minimum grants, stale grants, or other evidence; sampling/binding alone does not establish causality. Any subsequent behavior experiment requires an explicit hypothesis, frozen source and matched original regressions.

## Evidence-driven extension: full-width flow identity

The four initial observation runs completed exactly neutral with full selected grant coverage (110450 / 361322 rows, no cap omissions). Their analysis caught receiver IDs truncated modulo 65536. Receiver-side legacy records were uniquely joined to full original IDs using the low ID bits, source/destination IP and exact original size; all sends/receives then match. This is an analysis correction, not a workload change. Receiver grant allocation is mostly multi-sender contention; single-sender limited intervals contribute under 0.11% of aggregate eligible large-flow lifetime.

Confirmed source defect: FlowIDNUMTag stores an int32 ID and advertises 8 serialized bytes but writes/reads its ID with U16. Actual Packet tag round trips fail at 65536, 65552, 131088 and INT32_MAX. Fix the shared tag serializer/deserializer to U32 and initialize flow_size. Keep the tag's serialized size 8 and actual packet wire size unchanged. This applies to all protocols; cannot interpret old baseline comparisons as final after a shared simulator fix.

Prespecified new-source round: full original Storage30, Storage50, Web and Analytics seed301 with one Shared rescue GUARD configuration and HPCC, Homa, DCQCN, TIMELY (20 runs). Additional Storage30/50 grant-trace runs (2) verify complete full-width receiver identity and observation neutrality. Compare old/new same-arm FCT and metrics, retain all regressions, and validate all baseline results. No independent confirmation or paper promotion yet. Full DP2/All-to-All/other originals remain required subsequent regression coverage; do not declare the objective complete from these workloads.

## Focused global service-width experiment

Measured grant history places 21.34% of pre-fix eligible Storage50 large-flow lifetime under multi-sender caps <=100 Mb/s, versus <0.05% under single-sender limited caps. Test one globally fixed K=2 receiver service width, retaining the 12-BDP threshold, 128-BDP horizon, ACK rescue and all other Shared settings. Prior K=2 experiments with a 1-BDP threshold are not this condition.

Run K=2 on Storage30/50/Web/Analytics (4); fixed K=1/K=2 on Fabric/Receiver/Hybrid/Fairness/All-to-All/Ring/full DP2 (14). Total planned 44 original seed301 runs. No prefixes or per-figure configurations. Require original fairness Jain, Ring span/drops/RTO and full DP2 queue/tail metrics in addition to generic aggregates. Preserve every regression. Reuse same-source completed K=1 workload controls only. No independent confirmation or paper promotion.
