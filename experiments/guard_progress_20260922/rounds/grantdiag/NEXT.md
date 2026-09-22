# Active full-objective continuation

This turn made concrete progress: observation source, a reproduced and repaired full-width flow identity defect, 44 completed original runs and a rejected global K=2 experiment. All 44 simulations complete, zero failures, zero drops. Three driver launches failed before simulation (one missing runs parent, two missing profile due preparation path error); logs preserved. No live jobs. Full objective remains ACTIVE; no independent seeds, paper edits or Overleaf promotion.

## Sources

- guard-granttrace f82eb1b: parent guard-sizetrace 009738f; adds filtered grant allocation observations (original size, distinct senders, same-source flow count, minimum/total remaining and receiver sequence). Default off. Maximum 1M rows, minimum size 256001 in this diagnostic only. No traffic selection. Four old-source on/off Storage runs exactly match preceding source and all metrics.
- guard-flowid32 c2aedb0: shared FlowIDNUMTag declared int32 and 8-byte serialized size but used WriteU16/ReadU16. IDs above 65535 truncated at receivers. Fix WriteU32/ReadU32 and initialize flow_size. Actual Packet tag round trips fail before for 65536/65552/131088/INT32_MAX, all pass after. Tag length remains8; packet wire length unchanged. tests/flow_id_tag.cc committed. Keep this correctness repair. Legacy Getflowid() allocator API still returns uint16, but it is unused by the production SetId/GetId path; do not confuse the two.
- Both source worktrees clean/frozen. Original guard remains650811a, two user artifact directories untouched.

## Evidence

Initial grant traces: Ali30 110450 rows, Ali50 361322 rows; selected2983/4882 flows, eligible after original warmup1505/2430. Receiver IDs in old logs uniquely remapped using low16 ID, source/destination and original size. Every selected send/receive matched; no cap omissions. Fixed traces110432/363020 rows, direct full IDs match inputs, exact trace neutrality. Before/after cumulative large-flow FCT grant-state intervals are in grant_diagnosis*.json; these are NOT actual bottleneck time fractions. Source-path sampled binding evidence was previous campaign.

All 16 baseline workload runs (Storage30/50/Web/Analytics ×HPCC/Homa/DCQCN/TIMELY) retain exact FCT and all metrics after common tag fix. GUARD only changes Storage30/50; its other9 original scenes including fullDP2 exactly match the previous source. Ali30 GUARD mean+0.141%,P99slow+0.611%,queue+1.290%; Ali50 mean+0.0228%,P99slow+0.912%,queue−12.037%. Keep regressions, do not claim universal benefit from the bug fix.

Old large-flow grant-cap intervals: Ali30 multi-sender weighted35.744% / <=100Mbps9.728%; Ali50 weighted61.038% / <=100Mbps21.337%. Single-sender limited aggregate interval fraction only0.105%/0.042%. New source similar (Ali50 weighted61.326%,low21.190%,single0.064%). Grant delivery median4.1us and max4.4us. Work-conserving legacy option is ACTUALLY DISABLED by run.py (config guard_adaptive enabled0, interval200us); do not call absence of demand records a timer failure.

## Global width K=2 experiment

Same Shared rescue profile everywhere, only receiver_concurrency1→2, retaining min12BDP/horizon128. All11 original scenes covered; fullDP2 always1280flows/80buckets/25MB and fixed observation, no prefixes. Total44=4 original observation +20 fixed workloads/baselines +2 fixed observations +4 K2 workloads +14 K1/K2 other scenes.

K2 improves Storage50 mean22.940847→20.698245us(−9.78%),P99slow4.285566→3.943843(−7.97%),but queue3.906962→4.873520us(+24.74%). Homa mean20.143088us still lower. Web mean−1.37%,queue+13.82%. Analytics mean+2.71%,P99+11.66%,queue+32.24%. Receiver mean+17.63%,queue0.036991→0.743489us. Hybrid mean+20.39%,queue+91.94%. Ring ORIGINAL span11.709459→12.315509ms(+5.18%); no drops/RTO. Reject K2 as a universal configuration; do not mix K2 for Storage with K1 elsewhere.

K1/K2 exact full FCT/all metrics in Fabric,Fairness,All-to-All,DP2. Originalfairness Jain1 forboth,10–12ms zero-filled100us withall4flows active. DP2 still15.671423mean/85.400671P99/215.001914spanms/12.259150queueus, noRTO/PFC; sourcefix andK2 unchanged. Its originaltail/queuegapremains.

## Next useful action

Retain c2aedb0 as the corrected source base and K1 as global control. Diagnose whether preferred senders actually consume their grants under Storage multi-sender contention. Current per-flow grant trace lacks aggregate receiver DATA arrival and sender eligibility information, so do not assume underutilization from the cap states alone. Add observation-only cumulative receiver DATA counters (including unregistered traffic) or correlate existing appropriate counters, then validate exact neutrality. Use feedback/timing grounded in this evidence before implementing conditional service-width or unused-grant reclamation. Existing cap-aware variants and broad K sweeps were previously rejected; read their manifests before repeating. Single-sender shared-cap extension to small flows already caused Ring drops in guard_flowaware and is not a general repair.

Full original figure scope remains: workload mean/P99, original Storage bins, directed components, strict ablations/OFLM, original fairness, All-to-All/fullDP2 CDF and3queue ranks, Ring, supplementalseries/receiverwidth. Four-baseline independent confirmation and manuscript updates remain uncompleted. This turn was progress, never a no-progress/blocker turn. Freeze source/build while simulations live. Use absolute paths for checkpoint edits to avoid cwd mistakes.
