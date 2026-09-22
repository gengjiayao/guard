# GUARD follow-up experiments

The experimental implementation is in `/home/gengjiayao/ict/guard-balanced-cohort`,
branch `codex/guard-balanced-cohort-20260921`. Confirmation freezes commit
`0e3208af4eb6c15da47cc41ab44a712daa883122` and every binary/shared-library hash.
One configuration applies to all studies. No result is a promise of universal
dominance; read `REPORT.zh.md` for gains, tradeoffs and unresolved regressions.

The development matrix contains 312 attempts on observed seed 301. One
output-directory collision is preserved as a failed attempt; the separately
recorded retry follows the atomic reservation fix. The independent matrix uses
501–505 and contains 486 runs plus 8 instrumentation runs for the retained
two-sender time series. Main and supplemental figure families are all retained.

The older `guard_optimization_20260921` campaign also receives its previously
missing 75 runs on its unchanged source and profile. Its 401–405 observations
remain separate from this campaign.

## Reproduce or resume

Do not refreeze existing manifests. With the frozen worktree/build present:

```bash
python3 scripts/confirm.py run --workers 12
python3 scripts/confirm.py analyze
python3 scripts/report.py
python3 scripts/audit_figures.py
python3 scripts/plot.py --final
python3 scripts/archive.py
python3 scripts/final_gate.py
python3 scripts/make_report.py
```

The runner skips finished cells. The execution in this session uses disjoint
small, large-a, large-b and series shards. If spare workers assist an existing
scheduler, `scripts/assist_queue.py` records the exact unstarted frozen tasks it
reserves. A pending reservation is explicitly marked and is never accepted by
the final validation gate as a completed result.

`scripts/develop.py` records each source version, diff, configuration and build
hash in a separate round manifest. Its profiles are research trials, including
unsuccessful ones. Current source should not be used to rerun an old round
without reconstructing that round's recorded implementation.

## Validation and outputs

- `holdout/analysis.json`: validated identities and metrics for confirmation.
- `analysis.json`: development metrics and preserved failure record.
- `confirmation-evidence.json`: seed-paired percentage changes and pointwise
  t(4) 95% intervals; no multiplicity correction.
- `figures/`: comparison summaries; `figures/per_experiment/` contains all
  original data figure families as vector PDF and PNG.
- `raw_index.json`: compressed raw evidence for every finished attempt.
- `validation_checks.json`: full matrix coverage, frozen source/build/input
  hashes, matched ablation configuration differences and archive verification.
- `tests.json`: actual allocator and concurrent directory-reservation checks.
- `input-provenance.json`: topology hashes and compiler/interpreter versions.

The strict receiver-only control uses GUARD with `GUARD_FABRIC_CONTROL=0`.
Every other sender, receiver, ACK, window and traffic setting matches full GUARD.
The older CC-mode-13 receiver-only implementation remains as a separate legacy
control. Homa, HPCC, DCQCN and TIMELY retain their existing implementations.

The final gate requires all 494 confirmation runs to complete and preserves the
one developmental failure. Correctness checks do not establish performance
superiority. This evidence directory does not deploy or promote the candidate.
