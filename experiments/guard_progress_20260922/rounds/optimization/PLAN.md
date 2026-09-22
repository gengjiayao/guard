# GUARD optimization following the figure audit

User authorized implementation optimization and further experiments on 2026-09-21.
Previous manuscript campaign remains immutable. Source base: 650811a.

Development uses already inspected seeds 301–305 and all adverse workloads.
First isolate unsafe tail bypass, overly aggressive fabric target, and receiver
service concurrency. Keep input traces, topology, buffers, protocol baselines,
and accounting fixed. Preserve every attempted candidate, including failures.

Before confirmatory evaluation, freeze one shared profile and source/binary
hashes. Use newly generated paired traffic seeds across GUARD and all four
external baselines, plus a matched old-GUARD arm and internal ablations. Never
select a different GUARD profile per figure. Examine completion, flow identity,
loss/recovery, FCT, trace span, tails, and queues, including regression workloads.
Universal dominance is a research target, not an assumed outcome.

Initial finding: old ring seed 301 has 480/480 tail-bypass flows, zero HPCC rate
changes, and 2,907,875 egress drops. The 8-BDP threshold activates before a
bounded acknowledged tail exists for these 512-KiB messages.
