# Verified common GUARD profile

The controller and input protocol were frozen in f961ce2 before generating the final inputs. Both workloads use one configuration, now installed in `annual2026_tail_final_variants.json`. Updating this profile copies the exact parameters from the verified run plan; it does not change the controller or binary.

All 240 planned runs completed. Input flow identities and counts, every retained output hash, and independently recomputed overall P95/P99 passed audit. No slow flow, failed run, workload/load case or repetition was removed.

## Overall tail results

Values below are mean paired reductions against the fixed original Homa executable. Positive values mean lower FCT. Ten independent repetitions per condition; all message sizes enter each run’s overall percentile.

| Workload | Load | P99 reduction | P99 95% interval | P95 reduction |
| --- | ---: | ---: | ---: | ---: |
| AliStorage2019 | 50% | 14.285% | [12.459, 16.112]% | 8.222% |
| AliStorage2019 | 70% | 24.430% | [22.427, 26.433]% | 15.648% |
| AliStorage2019 | 80% | 16.549% | [12.880, 20.218]% | 18.215% |
| WebSearch | 50% | 19.325% | [15.593, 23.057]% | -30.945% |
| WebSearch | 70% | 18.253% | [14.432, 22.075]% | -67.195% |
| WebSearch | 80% | 11.998% | [8.499, 15.498]% | -86.243% |

All six P99 point-estimate means exceed the prespecified 10% target. This does not claim that their confidence-interval lower bounds exceed 10%, or that every individual run does so. WebSearch P95 regresses and remains fully reported; the optimization is not a universal reduction of every latency metric.

## Controller and comparison

The selected profile uses grant-bounded proactive release, continuous unused-grant reclamation, original-size receiver cohort classification, per-sender receiver budgets for substantial work, bounded sender priority with local cohort adaptation and a one-BDP completion tail. The optional rate-weighted sender scheduler and dynamic packet-priority experiment remain disabled because their measured joint effects were inferior. Earlier collective-specific adaptive/burst settings are disabled in this profile.

The baseline source is 6c438d7c7223d698bc2bea3333e8eac271fe002c. Its original executable and 62 shared libraries were archived and individually verified before any merge or rebuild. GUARD’s actual formal executable and libraries are separately archived. Complete runtime hashes appear in the frozen protocol and archive manifests.

## Scope and reproduction

Public WebSearch and AliStorage2019 size distributions with Poisson arrivals and uniform non-self destinations were simulated in ns-3. This is not a production packet replay or a physical prototype. The protocol fixes 16 hosts, 100 Gb/s links, 2:1 oversubscription, ECMP routing, 9 MB switch buffers and the exact generation/warmup intervals. All four algorithms use identical input traces and physical parameters.

`annual2026_generalization_verified.json` contains complete summaries, confidence intervals, health counts and frozen plans. Raw final records and audit/plot/package scripts remain under `experiments/results/generalize_final_audit`, `generalize_final_guard`, and the original repository’s `generalize_final_baselines`. The delivery archive retains all formal output files and development summaries.

Final inputs 7101–7110 have been observed. Any further controller tuning must treat them as observed data and reserve a new validation set before making another independent-validation claim.
