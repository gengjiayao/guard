# Full objective continuation: startup path feedback and joint control

Previous turn made progress (43runs/e70aacb). Objective remains all original paper figures versus all four baselines, with one global configuration and independent confirmation. No paper promotion or fresh seeds this development turn.

Original Analytics flow4572(11→14,8.496MB) has constant50Gbps fabric estimate throughout its lifetime with startup enabled, versus100Gbps disabled; no hpcc events. Its same-rack path has no remaining fabric hop after receiver-hop removal. Competing flow4260(7→14) is delayed by aboutthe same0.65ms. Three original Analytics diagnosticruns confirm this behavior; traces retain all flows and results.

Fix: mark only a reduced initial startup estimate as awaiting the first ACK. If that ACK contains no remaining fabric hop, restore the initial fabric estimate to line rate and still compose it with receiver grants. Once the first ACK has valid fabric hops, clear pending state and never reset learned rates on later no-hop ACKs. Explicit trace event records a release; no unsafe generic rate reset.

Merge existing bounded feedback recovery and same-peer startup in a separate worktree; preserve both options and test actual helpers. FullDP2matched ablations plus four baselines, then all relevant original regression scenes. Observed seed301 only. Retain every failed/rejected outcome. Freeze exact harness/source/build per round and archive raw evidence.

Port-level prior evidence locates normal-gain queues onToR→spine uplinks, whereas lambda1 worstport isToR→receiver and residualuplinkqueue remainsaboveHPCC. Add a complete2x2 diagnostic underfixedlambda1: ACK8/ACK1 andreceiver-hopexcluded/included, usingSharedwithoutstartup/recovery. Sameinputsandbinary, allfourcellsretained; testfeedbackcadence versusomittedreceiverqueuefeedback. These arecausalcontrols, notper-figuretuningorautomaticallypromotableprofiles.
