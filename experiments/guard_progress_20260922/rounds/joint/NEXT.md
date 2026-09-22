# Remaining objective and next causal work

The full original-figure / four-baseline goal remains ACTIVE. This round made real progress: a causally traced stale startup estimate was fixed; both mechanisms were combined; ten original scenes and a full feedback factorial were measured. No independent confirmation or manuscript promotion.

Frozen source: guard-joint, commit 5a14a82 (parent merge 1cafdeb, recovery parent 778d95a). Current evidence includes 61 complete simulations, observed seed301 only. All live jobs have finished; do not rerun these completed rounds. Four exact trace/no-trace FCT+metric pairs, five complete controller traces, four actual helper tests, source/build/input/harness/archive hashes verified. Eight figures include all adverse results. Original guard HEAD650811a remains untouched.

Findings to preserve:
- Analytics flow4572 same-rack startup fabric estimate remained50Gbps because no fabric hops remained after last-hop removal. First-feedback release fixes this initial estimate only, retaining receiver limits and later learned estimates. FCT5354.454→4703.576us versus4702.810us startupoff. Whole-trace startup regression almost eliminated; this is not an external-baseline win.
- Joint32 fullDP2 mean16.454ms/P9957.846ms/queue26.051us, versus same-build Homa17.504/46.134/57.823 and HPCC28.677/72.094/.213. Two PFC pauses inJoint32. Joint8 mean16.509/P9967.125/queue19.538. Shared15.932/93.682/12.411. CompleteCDF still crossesHoma.
- Joint32 λ1 mean21.937/P9970.141/queue2.706,16timeoutrecoveries. This is not universally better thanShared or externalbaselines.
- Ten-scene regressions: joint8 storage50mean−.90%/P99slow−1.16%/span−1.91%/queue−8.16%; joint32storage50P99slow+1.05%,queue+.44%. BothWebP99slow+1.07%,Alltoallmean+.075%/P99slow+1.47%/span+.38%. Ringjoint8/32queue+34.51%/+38.98% despite lowermean/span. All percentages versus same-buildShared; all results retained.
- Fixedλ1 ACK8+omitlast: mean24.295/P9999.605/queue3.530; ACK1+omitlast36.821/125.812/6.793; ACK8+keeplast24.034/89.990/.817; ACK1+keeplast31.040/81.887/1.246. Keepinglast reduces receiver-classworstmean3.530→.093us andfabric2.401→.817us, stillaboveHPCCfabric.213us. ACK1 worsensmean/span inbothcells. FAST_REACT=0 inallcells; do notattribute this tofastreact. Actualcause ofACKcadenceregressionnotyetisolated.
- BaselineHoma changedslightly acrosssourcebuilds, plausiblyallocation/order effectsbutnotyetdiagnosed. Usecurrent matchedbuildvalues, nothistoricalonesaspairedsamples. No deterministicbaselineclaim.

Next concrete work:
1. Separate residualfabricqueuecontrol fromsender scheduling/feedback starvation. Tracequeue+transmit/ACKtiming onfullDP2 withanobservationallyvalidatedtracer. Keepbaseline andtraceoffpairs; no prefixsubstitution.
2. MeasureACK wirevolume and NIC service delays beforeclaimingACK1 failureisoverhead. Consider a diagnostic thatdecoupleswireACKcadencefromrate-controllerupdatecadence; thismustbeexplicitlylabelledcausal, notrealprotocolgain. No broadnewparametersweepswithoutacausalhypothesis.
3. Checkwhy low-gainjoint32 triggers16timeouts: distinguishgenuinedataprogressstall fromcontrol/pacingdelay. Do nottuneRTOjusttohideevents. Retainrecovery/PFCcounts, notonlyzero drops.
4. Receiverlast-hopfeedback iscurrentlydiscarded fromfabricloop bydesign. Ifusingitlocallytoregulatereceiverqueue, designenforceableaggregateper-peercredit/pacing; per-flowcapC cannotcapaggregateNICtoC whenmanyQPs active. Do notreadhiddenroutingstateorassumedpathidentity.
5. Use one global candidate acrossalloldfigures, including workloads,sizebins,fabric/receiver2/hybrid,strictablations,OFLM,fairness,Alltoall/fullDP2,Ring,supplementalwidth/series. Fresh independent seeds onlyafter viablecandidatefreeze; failuremeansretainresultsandcontinue, nevercherry-pickperfigure.
6. MITCommLab/paperwritingrewrite andOverleaf updates remainauthorized later whenevidence supportsclaims. Do notpresent currentprototypesasdominant, allzeroPFC, or independentlyconfirmed.
