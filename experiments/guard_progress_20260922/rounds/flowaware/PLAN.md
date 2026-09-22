# Active objective

Continue until each original paper data figure demonstrates GUARD benefits
over every external baseline, or improvements on some of its metrics with
no degradation on its other metrics. Preserve the original experiment set,
matched HPCC/Homa/DCQCN/TIMELY comparisons, raw outcomes and adverse results.
Source changes and a common deployable configuration must explain the gains.
Do not remove hard cases, select per-figure profiles, or relabel mixed results
as success. Keep the goal active while a required comparison is unresolved.

The preceding turn made progress: it completed 494 fresh confirmation runs,
75 previously missing runs, actual allocator checks and complete figure audits.
It did not achieve the objective. Frozen evidence remains in
`../guard_balanced_20260921`; do not change those observations.

Current hypothesis: multiple large messages sharing a source/destination
compete under receiver weighted sharing even though the sender also chooses
the shortest eligible message. Per-flow pacing may spread service across
messages and raise mean completion time. Test opt-in ordered grants for a
single-source receiver cohort, retaining the multi-source fairness rule.
Use matched fabric-feedback-off probes to separate scheduling from feedback.

Development uses previously observed seed 301. New successful candidates will
need fresh seeds, all original figures, matched ablations and all baselines.
The new independent seed set must be frozen before any outcomes are opened.

Source worktree: `/home/gengjiayao/ict/guard-flowaware`.
Each development round records a committed source, binary/library hashes,
all exact task configurations and input/topology hashes. Failed attempts remain.
