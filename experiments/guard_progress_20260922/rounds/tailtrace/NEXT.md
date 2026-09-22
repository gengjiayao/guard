# Next causal optimization, full goal retained

Current evidence indicates a persistent per-flow fabric-rate inequality, not receiver cap starvation. In original full DP2, the slowest1% flows have about74% sampled rate caps below1Gbps, receiver grants100Gbps and essentially no window blocking. Removing fabric control shortens tail but inflates queue; RR does not fix it. Startup sharing improves DP2 mean but regresses Web and does not eliminate tail.

Inspect UpdateRateHp with actual frozen config: RATE_AI40Mb/s, MI_THRESH0, U_TARGET0.95, GUARD_LAMBDA1.8, ACK interval8. The per-full-feedback update is R_new=R_old/c+40Mb/s (clamped). For a persistent c=1.3, its equilibrium is about173.3Mb/s, consistent with the observed slow-flow caps; this arithmetic is not proof that every slow flow has constant c. New flows start from100Gbps and share the same physical sender link; different update cadence and path congestion can perpetuate rate imbalance.

Next bounded hypothesis: normalize additive recovery by elapsed full-feedback time relative to original baseRTT, with a conservative bound and correct inactivity/zero-time handling. Log full-feedback spacing and stored congestion state to distinguish slow feedback recovery from persistent true congestion. Test with matched fixed-gain controls and retain queue metrics, since faster recovery may worsen queues. Do not disable network control, reset arbitrary rates on every receiver grant, or promote a configuration merely because mean beats Homa.

A separate principled refinement, if useful: limit startup sharing to large messages directed to the same peer rather than every large local message. Current helper couples independent destinations, which may explain Web regression. It is NOT yet implemented or validated. FullDP2 has one peer per source, so this refinement is expected to leave the mechanism there unchanged, but still needs actual replay.

Reproducibility fix992cc57 orders legacy grants by flow ID. Full trace-on/off comparisons are required in validation_checks.json. This does not certify every optional allocator or baseline as independent of heap layout. All future comparisons must freeze one binary and use fresh matching inputs.

Original scope remains all original figures (including storage size bins, directed bottlenecks, all ablations, fairness, collectives, Ring and supplements) against HPCC, Homa, DCQCN and TIMELY. No new independent seeds until a single global candidate justifies confirmation. Original worktree and Overleaf remain untouched by these development probes.
