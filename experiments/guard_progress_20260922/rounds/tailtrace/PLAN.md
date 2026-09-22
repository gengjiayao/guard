# DP2 causal tracing continuation

Previous goal turn: progress (176 completed development simulations, full archived evidence d269ffd).
Full objective stays active: all original paper figures and all four baselines; improve some metrics with others tied. No paper promotion before independent confirmation.

1. Add opt-in per-flow spaced controller snapshots with sender byte progress, ACK position, transport window, pacing deadline and cumulative transmit bytes. Trace defaults unchanged; complete events bypass time sampling but obey row cap.
2. Replay original full DP2 at development seed301 with shared128 profile, with and without tracing. Require all1280flows complete; compare tracing influence and count cap omissions.
3. Causal fabric-off diagnostic with same receiver and sender settings distinguishes fabric throttling from receiver/scheduler restrictions. This is a diagnostic, not a promotable queue-safe solution.
4. Analyze full-trace slow flows; use measured bottleneck for next code change. Preserve all attempts and exact source/build/input hashes. New seeds remain unopened.

Causal results: fabric-off eliminates most DP2 tail but grows queue to68.6us; RR does not cure the low-rate tail. Added fair-share startup probe and stable flow-ID grant enqueue order to address new-flow bursts and trace-on/off nondeterminism. Full8-arm stable-build replay includes all four external baselines. A2-arm target diagnostic enables existing queue-adaptive target for long messages, with/without startup sharing, to test whether lower congestion equilibrium removes the slow-flow bottleneck. All remain development seed301.
