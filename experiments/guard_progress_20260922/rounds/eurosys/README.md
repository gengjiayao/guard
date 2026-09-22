# GUARD EuroSys 2027 remeasurement

This evidence repository contains fresh measurements for the current `guard` implementation, the rewritten manuscript, and scripts that derive its figures and numerical claims. The earlier Conext and EuroSys source archives are preserved separately in `backups/`; their performance numbers are not inputs to the new analysis.

## Frozen implementation and scope

- Simulator source: `/home/gengjiayao/ict/guard`, revision `650811a90e618bf4db1b7dd160c83cc798637b7e`.
- `manifest.json` records the executable hash, driver hash, five seeds (301–305), all input hashes, and every treatment.
- Main GUARD profile: current driver defaults, lambda 1.8, old-estimate weight beta 0.125, gamma 1, remaining-aware grants, static size priorities, bounded sender SRPT, selective registration, proactive release, ACK interval 8, short/tail bypass. Optional later policy variants remain disabled.
- External protocols: HPCC, Homa, DCQCN, TIMELY. The simulator independently reimplements Homa. Homa uses its native priorities and recovery, including no PFC on data queues. See manuscript for baseline limitations.
- 350 original campaign cells plus 42 coverage cells = 392 simulations. The extension restores the old two-sender incast and directed time-series views without changing controller settings. `audit/manifest-initial.json` preserves the original campaign manifest.

## Regenerate the evidence

Python 3 requires NumPy and Matplotlib. The simulator itself builds with the repository's Python-2-compatible waf driver. No algorithm source changes were needed for this campaign.

```sh
python3 scripts/analyze.py
python3 scripts/make_results.py
python3 scripts/plot.py --final
bash paper/build.sh
bash paper/build.sh supplement
```

`analyze.py` checks input/config hashes, completion multiplicity and identity, positive timings, and common flow sets across arms. Its cache fingerprint includes raw file content, result metadata, analysis code, and the imported parser. Missing or invalid results prevent the final plotting gate. Each original flow appears exactly once; warmup filters arrivals only, never protocol-dependent completion times.

`claim_evidence.json` maps each generated number to seed-level values and paired run keys. `analysis.json`, `metrics.csv`, and each run's `metrics.json` retain measurements and bin sample counts. `raw_index.json` maps run keys to compressed raw snapshots and hashes. A snapshot contains its exact config, input, FCT, queue, PFC and mechanism-counter files, plus time series when enabled. The source `output_dir` remains in the result metadata; archive names permit relocation without depending on that original directory.

To repeat the campaign in this workspace after restoring the frozen simulator executable, use `python3 scripts/campaign.py run --workers 4`. Existing result records make this command resume completed work. To conduct an independent repetition, copy scripts and the frozen manifest/flows into a new campaign directory and omit its `runs/`, caches, and derived outputs; update the source repository path in the scripts if necessary. Do not reuse a result record from another executable or input. Do not run `prepare` over an existing manifest.

## Metrics and limits

- Random traces inject for 10 ms and exclude arrivals in the first 5 ms from FCT statistics. Directed and collective traces include all flows.
- Slowdown is max(1, FCT / simulator ideal FCT). The ideal includes base RTT and payload-plus-fixed-header serialization, excluding INT, queueing, and extra protocol control traffic.
- The plots report the mean of five seed-level statistics and Student-t 95% intervals. Relative effects use paired per-seed percentage changes. Tiny directed jitter does not represent arbitrary routing variability.
- Queue comparisons use fixed observation windows with zero padding after early completion: 10 ms random, 100 ms fairness, 250 ms DP2, 20 ms other tests. Byte occupancy converts to equivalent serialization time at 100 Gb/s, not measured packet residence time.
- Send-rate plots reconstruct omitted zero samples. Each sample covers 100 us; the Jain index uses per-sender mean rates on [10,12) ms.
- DP2 and ring inputs are open-loop communication shapes. Their completion spans are not training job completion times or dependency-aware All-Reduce measurements.
- Losses and recovery remain in the results. The default GUARD profile performs poorly on ring stress; this is not a lossless-only selection.

`audit/experiment_coverage.md` maps all earlier experiment families to current measurements. Independent reviews and their corrections are recorded under `audit/`. `paper/main.pdf` is the main paper; `paper/supplement.pdf` carries additional directed time series and fan-in-width plots. Numerical data appear as figures, not numerical tables.

Distribution provenance: AliStorage2019 matches the HPCC artifact byte-for-byte; WebSearch has identical numeric CDF points. The repository's denser FbHdp2015 CDF differs from the HPCC artifact's coarse FbHdp table, so the manuscript identifies the exact local representation. `audit/distribution-provenance.json` records this check, and `flows/distributions/` freezes all three source CDFs.
