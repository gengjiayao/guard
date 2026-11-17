# GUARD joint P95/P99 validation

One frozen congestion-control configuration passed both overall tail-latency
targets on AliStorage2019 and WebSearch at 50%, 70% and 80% host payload load.
Each case uses ten new independent inputs generated after protocol freeze.
Mean reductions are calculated from paired per-run percentiles; all twelve
P95/P99 means exceed 10% versus the predesignated original Homa execution.
They also exceed 10% when compared to the lowest corresponding percentile
from three predeclared Homa executions per input. Original Homa source and
runtime were retained unchanged. All 360 runs and complete input flow
identities were independently audited; no completion-window censoring occurs.

See joint2026_verified.json for actual values, intervals and provenance,
joint2026_final_variants.json for the common profile, and
joint2026_final_protocol.json for the frozen comparison protocol.

The selected profile combines receiver grant scheduling, bounded proactive
release, sender remaining-work scheduling, drain-before-promotion priorities,
and ACK-aligned INT compaction. Compaction removes unused wire telemetry,
not payload; required scheduled ACK telemetry remains present. Native tests
and all 60 final GUARD runs verified this invariant. Proactive release remains
enabled. Unselected experimental options remain available but disabled in
the final profile. Negative development results remain in joint_probe*.

Full results live under experiments/results/joint_final_audit in the joint
worktree; original baseline runs live in guard-fixed-reference-20261117.
The portable archive preserves all 360 raw FCT files, 60 input traces,
configuration, statistics, analysis, code history and development summaries.
Full output logs and frozen runtime archives remain on node67.

The findings apply to the specified ns-3 workload distributions and loads,
not a physical prototype or production packet replay. Inputs 91001–91010
have now been observed and must not be treated as unseen in future tuning.
