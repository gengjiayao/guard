# Active full-objective continuation

Previousgoalturnmadeprogress:79mainfullrunsplusfourfilteredStorageobservationsplanned(total83),guard-ackrescueaa3691e andguard-sizetrace009738f. Noindependentseeds, no manuscriptorOverleafpromotion. Do not markgoalcomplete: originalallfigure/fourbaseline/trueadvantageortiesrequirementremains.

Sourceguard-ackrescueaa3691e adds default-offguard_sender_ack_rescue. OnlyreadyGUARD/nonIRNflowswithpositiveflight<ACKbatch, unsentbytes, andexistingrecoverytimerinitslatterhalf maypreemptSRPT. Latchedcurrentuna+ACKbatchtargetensurestheexistingtimer'sresetoneachsentpacketdoesnotdefertheotherpacketsforanotherhalfRTO. Respectspacing/window/PFC; ackcancel/finished/identitychangesreleasependingstate; ifblockedserveotherreadyflows. Defaultoff, RTOunchanged, noACKtimerornewcontrolpacket. Actualunit tests thresholdboundary, latchacrossrealEventIdrearm,eightexclusions,earliestdeadline. No per-scene tuning.

39initialruns:fullDP2threeparents(cursorShared,Joint32,Sharedλ1)×rescueoff/on plusfourbaselines plusoneSharedλ1rescuetrace(11);SharedtenoriginalnonDP2scenes×off/on(20);Joint32Web/Analytics/Alltoall/Ring×off/on(8). Thenfourbaselines×tennonDP2scenes(40),total79. Eachroundfreezesbuild/source/input/harnesssnapshot. Allobservedseed301. OriginalDP2always1280flows80buckets25MB,2GB/host,.25squeueobservation; no prefixsubstitution.

Measuredpreliminaryrescueeffects:SharedP9988.793→85.401ms,span216.534→215.002ms,queue12.478→12.259us,mean15.668915→15.671423ms(+0.016%,notvalidatedtie). Sharedλ1RTO3→0,mean24.482→24.338ms,queue5.313→2.905us,span227.558→226.592ms,butP99103.222→103.637msworsens. Joint32rescuenointerventions/FCTexact. AlltenShared/fourJoint32nonDP2pairs have0interventions andFCT/allmetricsidentical, preservingoriginalAlltoallpriorityperformance. Healthyneutralityisnotbaselineadvantage.

FourcurrentbaselineDP2controlsplus3GUARDparentsmatchpriorbuildexact, includingHomaRESENDstableorder. TIMELYtook622.9CPUwallsecondsbutcompletedwithbyte-identicalFCT/allmetrics; a longrunningjobmustnotberestartedbasedonobservationtimeout. No simfailuresinthe79mainruns; RingDCQCN/TIMELYhavelargeactualdrops(preserve,notrunfailures).

FullStoragegapdecomposition:ali30GUARD−Homamean−.013442us,large256KB–2MBbin+0.23602usoffsetbysmallerbins. Ali50mean+2.792521us,2430eligiblelargeflowscontribute+3.14691us,allsmallerbinsnegative. Small-flowthresholdoroverallqueuealonecannotexplainthecause. FocusnextcausalanalysisonlargeStorageflows, not more indiscriminateDP2parametersearches.

Observation-onlysourceguard-sizetrace009738f addscontroller_min_flow_bytes default0; beforetraceattempt count, eventswithqp->m_sizebelowthresholdincrementsize_filtered_out andreturn. No trafficselection. Newthirdfooterline logsfiltercount/minsize. FourfullAli30/Ali50runs Sharedrescuewithtraceoff/on,filter256001,sample10us,300kcap. Requirecompleteallflowmetrics, everyselectedflowcompleteevent, no capomissions, exacttraceandcrossbuildFCT/allmetrics. Sourceandbinaryfrozenwhilejobsrun.

Originalfigurecoverage remains broaderthan11scenemean/tail/span/queueaudit: architecture,workloads,sizebins,directedfabric/receiver2/hybrid,strictablations,OFLM,common-intervalfairness,Alltoall/fullDP2CDF+threequeueranks,Ring,supplementaltimeseriesandreceiverwidth. original_metrics.py reconstructsfairness100uszerosand10–12msJainwithallfourflowsactive; Ringusesoriginalspan/drops/genericRTOwithnativeHomaRESENDseparate. Do not callRingbadsolelybecauseextragenericmeanFCTmetricloses1%; inspectoriginalfiguremetrics. Needalloriginalablations/supplementalcurvesandindependentconfirmationbeforepromotion.

Evidence scripts: summarize.py,archive.py,verify.py,report.py,status_plots.py,original_metrics.py,storage_gap.py,size_diagnose.py. Verify83terminalrecordsandallhashes afterthefourfilteredobservationsfinish. size_diagnose usesactualcontrollerbindinglabels(grant includes tailbypass), reportsper-flowmeansofsamplefractions; these are NOT exacttimefractions orproofalllatencycausation. Retainrawnumericalcaprelationships too.

Finalterminalstate,visualreviewandevidencecommitwillbeappended. Do notinfercompletionfromthisplan. No AGENTS.md; no agents spawned. Originalguard650811aandtwouseruntrackedartifactdirsuntouched.


## Final verified checkpoint

All 83 original development-seed-301 simulations completed; zero failed attempts. Source/build/input/harness/archive hashes verified. All 15 figures visually inspected; event-label headroom and overlapping log tick labels corrected. No live simulation/build jobs at checkpoint. No independent seeds, manuscript edits or Overleaf updates. Goal remains active and this turn made concrete progress.

Sources: guard-ackrescue aa3691eb25a80347e55889b95e8c84e3f3ee543e; observation-only guard-sizetrace 009738fcfa3a5d9ae96815da728b0191b58f8110. Both clean. Original guard remains 650811a90e618bf4db1b7dd160c83cc798637b7e with its two user artifact directories preserved.

The four Storage observation runs are now complete. Both on/off trace pairs and cross-build controls have identical complete FCT and all metrics. Selected flows 2983/4882, eligible after original warmup 1505/2430; every selected flow has a matched completion, no cap omissions. Mean per-flow sampled receiver-selection fractions are 69.1226% / 86.4617%; selection also below 100 Gb/s is 39.92% / 76.01%. Fabric-selection fractions 3.7551% / 4.0648%. These are diagnostic observations, not exact time shares or causal proof.

Current Shared rescue still loses Storage50 mean to Homa by 13.86%, Web mean by 15.42%, Analytics mean by 1.20%, Fabric mean to HPCC by 3.27%, All-to-All mean to Homa by 13.20%, and full DP2 P99 slowdown to Homa by 86.92%. Queue deficits also remain (see current_baseline_gaps.json). Original fairness Jain is 1.0; original Ring span 11.709459 ms with zero drops and generic RTO. Do not classify those original figures by extra generic mean-FCT metrics. Strict ablations/OFLM/supplementary figures and independent confirmation remain uncompleted.

Next useful source work: diagnose receiver grant allocation for original Storage large flows using existing full selected-flow traces, then add observation-only receiver-side records if needed. Check active-flow lifetime, demand/remaining-byte freshness, idle grant allocation and receiver utilization before proposing a globally applicable change. Numerical receiver selection alone is not proof of a bug. Review prior rejected settings to avoid repeated sweeps. Preserve complete workloads, warmup/bin rules and four baselines. Keep build/source frozen while jobs are live. No per-figure parameter choices or selective omission.
