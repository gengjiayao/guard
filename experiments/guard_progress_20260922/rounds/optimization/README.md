# GUARD optimization evidence

This directory records implementation experiments following the September 21
figure audit. It preserves favorable and unfavorable results. The candidate
remains experimental; a Ring improvement alone does not justify replacing the
previous profile.

Implementation worktree: `/home/gengjiayao/ict/guard-optimization`.
Branch: `codex/guard-scope-safety-20260921`.
Tested confirmation source: `17df5795f9ddf0dafe5dedb5d38e4371798eefe7`.
The source documentation is `docs/guard-scope-safety.md`.

Development uses already observed seed 301. The confirmation profile freezes
five options for every workload: guarded, revocable tail bypass; adaptive
fabric target; queue budget 4 BDPs; receiver concurrency 1; elephant threshold
12 BDPs. Remaining options retain the defaults. Confirmation uses new seeds
401–405, equal input hashes within each comparison, and all four external
baselines in the smaller workloads. Large-workload regression checks compare
the candidate with the previous GUARD profile. Full configurations and shared
library hashes appear in the manifests and run records.

The candidate processes feedback during guarded tail bypass. Its legacy
receiver allocator avoids redundant concurrency limiting when only one source
NIC sends to the receiver. `scripts/check_scope_safety.py` checks these changes
against actual network runs, including preserved failed-control examples.

Important files:

- `REPORT.zh.md`: outcome, limitations, and promotion decision.
- `confirmation-evidence.json`: five-seed paired effects and their source runs.
- `figures/optimization_effects.pdf`: changes relative to previous GUARD.
- `figures/baseline_comparison.pdf`: comparisons with the external baselines.
- `figures/safety_and_fairness.pdf`: Ring loss/completion and fairness tradeoff.
- `holdout/confirmation-manifest.json`: immutable planned matrix and hashes.
- `holdout/analysis.json`: validated results for completed confirmation runs.
- `raw_index.json`, `raw/`, `holdout/raw/`: hashed archives of finished attempts.
- `*-manifest.json`, `runs/`: all development candidates and failure records.

The runners reuse the prior campaign's frozen configuration and analysis tools
from `../guard_eurosys_20260921/scripts`. Both evidence directories must remain
available. Simulator output directories are recorded in each run, while raw
archives retain snapshots independent of those live paths.

The executed confirmation shards can be resumed without changing the profile:

```bash
python3 scripts/confirm.py run --studies fabric receiver hybrid receiver2 fairness alltoall ring web40 fb40 fabric_series hybrid_series --workers 10
python3 scripts/confirm.py run --studies ali30 ali50 allreduce_dp2 --arms guard old_guard --workers 8
python3 scripts/confirm.py analyze
python3 scripts/report.py
python3 scripts/check_scope_safety.py
python3 scripts/archive.py
```

The full manifest also contains additional large-workload baseline and OFLM
runs. They are not represented as completed measurements. They are needed
before any complete replacement of the manuscript evaluation. The current
manuscript and previous 392-run evidence campaign remain unchanged.

Intervals are pointwise t(4) 95% intervals on five seed-paired percentage
changes, without multiple-comparison correction. Queue comparisons retain the
prior campaign's fixed sampling-window definition. A mechanism check passing
does not imply better performance, and the report retains that distinction.
