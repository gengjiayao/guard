# Figure derivation map

All vectors derive from `scripts/plot.py --final`, which requires every frozen run and no failed validation. The common palette, line styles, markers, and bar hatches distinguish protocols at 10-point final-size labels. All figures use a 7-inch canvas for full-width placement.

- Architecture: inline TikZ in `design.tex`; sender cap composition, shared links, receiver lifecycle, grant and stripped-telemetry feedback.
- Workloads: paired per-seed changes in mean FCT and P99 slowdown; zero reference and Student-t 95% intervals prevent implying an improvement when effects cross zero.
- AliStorage 30% and 50%: mean/P95/P99/P99.9 slowdown for all eight CDF bins; logarithmic y scale; sample counts remain in analysis JSON.
- Directed: mean FCT and busiest-port fixed-window mean queue for fabric, original two-sender incast, mixed geometry.
- Ablations: mixed-geometry FCT, queue, and actual fabric-binding counters for full, final-hop retained, lambda 1, lambda 1.4, and receiver-only GUARD.
- OFLM: mean FCT, grant messages, and mean per-flow goodput for full and individually/jointly disabled lifecycle mechanisms.
- Fairness: zero-filled 100-us step traces for four staggered flows; paired common-interval Jain index uses [10,12) ms, when every flow remains unfinished.
- Collectives: communication span, seed-301 FCT CDF, and mean queue at each of the three busiest port ranks. DP2 remains open-loop and cannot measure training JCT.
- Ring stress: span, drops, timeouts. Symmetric logarithmic axes retain zero-loss arms as well as very large drop counts.
- Supplemental directed time series: seed301 sender0 rate and maximum-port queue; instrumented repetitions match base completions byte-for-byte.
- Supplemental fan-in widths: two/four sender FCT and busiest-port mean queue, five seeds.

The negative outcomes remain in the plots. These figures describe the current frozen implementation rather than choosing parameters after looking at comparative results.
