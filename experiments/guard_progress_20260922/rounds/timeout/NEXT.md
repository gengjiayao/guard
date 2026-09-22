# Next work: preserve full objective and causal evidence

Goal ACTIVE; previous turn made concrete progress, not a no-progress/blocker turn. All90attempts terminal:75complete,15preservedfailures(10missingconfighelper,2unsupportedtracecap,3initialpacket-lifetimeprototypecrashes). Separatebootstrapfailedbeforeper-runrecords. No live jobs, no fresh independentseeds, no paper/Overleafpromotion. Do not rerun finished rounds.

Full originalfigure/fourbaseline objective stays intact: workloads, AliStorage30/50sizebins, fabric/receiver2/hybrid, strictcomponentablations, OFLM, fairness, Alltoall/fullDP2, Ring, supplementalseries/receiverwidth. All originaltraffic retained. Thiscampaign tests developmentseed301 only.

Frozen source revisions:
- guard-timeoutprobe: 968b0b0266955855ddce63304f89a14208226812
- guard-ackdeadline: b2ecf0411588a52b12efc6d0a90ef57fcf3bb60c
- guard-ackbounded: 4e35d7c89e760bf7ee97fc807bbb6abd33706be4
- guard-ackidle: 8ed9d68d971a404fa9542bb3fa9e1d0aa02ee3e9
- guard-faircursor: 6febd7d8d51cb6518042c8390f05270df6cb2e06

- timeoutprobe: observation only, mandatorytimeout rows and actualhostserializedpacket/byte counters attachedtoPHYTxBegin whencontrollertraceenabled. Wirebytesincludeheaders,excludeIFG; allocationprecedesflows andpacketcountsusepreallocatedarrays.
- ackdeadline: initialpartialACKdeadlineprototype, passedcancellationhelperunitbutthreeintegrationscrashed becauseuppernetworkstackmutatedretainedpacket. Keepfailedsourceandrawattempts.
- ackbounded: packetcopy+explicitINTparsing fixescallback. Newguard_ack_max_delay_rtts default0; onebaseRTT profiletested. Deadlinefromfirstsuppressedpacket, retainlatestINT, cancelonnormalACK/NACK/completion/deletion. ActualtimerboundsverifiedagainsttopologymaxRTT. No RTOtuning.
- ackidle: actualCancelGuardIdleRetransmit helper cancelsnonIRN GUARDtimerswithzerooutstandingbytes; HandleTimeoutprotectsemptyflight. Outstanding-data/IRNtimerspreserved. FourcrossbuildFCTfilesidentical; joint32_l10timeout16→15only, othermetricsunchanged. Withdeadlinebothλ1profileshavezeroRTOs, butlatency/queuecanregress.
- faircursor: optionalguard_sender_fair_cursor default0, SettingsglobalonlyusedbyGUARD SRPT. Separatem_guardSrptFairLastIndex advancesonlyonfairnessturns; original64packetquantum retained. Actualschedulerreproducer650dequeues/fouralwaysreadyflows640/10/0/0, actualfix640/4/3/3; testsretainpaused,pacingblocked,windowblocked,finishedflowexclusions. SixfullDP2pairedruns+fouroriginalcases×fourprofiles16runs. Fullten-scene/fourbaselineconfirmationnotdoneforthislatestrevision.

Key causal evidence:
- Originalλ1Joint32+Shared18timeouts:17outstanding1–7KB(<8packetACKbatch),1emptyflight. Pacingdeadlines~4msinthepast, ratesmostlyseveralGbps; NICservice starvation pluspartialACKwaiting is supported, notproofthatalltailscomeonlyfromthiscause.
- ACK8 sends4,001,280ACKs/376,120,320B; ACK1 sends32,000,000ACKs/3,008,000,000B. Data32Mpackets/34.88GBplus64retransmittedpacketsinthetwotimeoutprofiles. Controlbytefraction~1.5%vs~8.5%. Do notclaimisolatedcausalityofwireoverheadversusfeedbacktiming.
- Fiveinitialtracepairsbyte-identicalFCT/allmetrics; twoACK1traceshit300kcap. Preservethem. Repeatedwith1mssampling, same300kcap; mandatorytimeout/completioneventsunsampled. Twosparsepairsalsobyte-identicalandcomplete. Boundedandidledeadlinepairsidenticaltoo:9pairsvalidated,5completeprimarydiagnostictraces+2deadlinecomplete traces.
- DeadlineSharedten-sceneeffectsincludeRingmean+1.93%,queue+78.68%,despitelowerspan/P99slow; Ali30queue+~9.3%,Ali50queue+3.5%. Do notpromoteasglobalwin.
- Joint32+deadline(fullnormalgain)DP2mean15.643ms/P9948.639ms/span216.870ms/queue37.925us, butPFC7460. ThisisworsePFCthanTIMELY3873. Allcompleteattemptshavezero drops, whichdoesnotexcusePFCregression.
- NewbuildHoma17.733ms/P9951.224ms/queue56.067us differsfromoldbuilds(17.504/46.134). Useonlymatchedbuildbaselines andinvestigatedeterminismbeforecrossbuildadvantageclaims. HomaScheduler::StallCheck iteratesunordered_map<RdmaRxQueuePair*,...> andemitsRESENDsinpointerhashorder; currentbaselinehas10,328resends. Thisisaplausibledeterminismcause,notyetproven. Donottunebaselineoutcome.

Selected latest DP2 metrics (mean/P99/span milliseconds, queue microseconds):
- cursor_shared: 15.932222 / 93.682159 / 216.360675 / 12.410542; RTO0; PFC0.
- cursor_shared_cursor: 15.668915 / 88.793154 / 216.534419 / 12.478155; RTO0; PFC0.
- cursor_joint32: 16.454371 / 57.846190 / 217.393860 / 26.051393; RTO0; PFC2.
- cursor_joint32_cursor: 16.449827 / 58.835300 / 216.961442 / 24.707438; RTO0; PFC26.
- cursor_joint32_l10_deadline: 25.742101 / 65.430572 / 230.723593 / 13.716109; RTO0; PFC0.
- cursor_joint32_l10_deadline_cursor: 25.730067 / 66.192713 / 230.863325 / 14.704507; RTO0; PFC0.

Sharedcursorimprovesmean1.65%andP995.22%, queue+.54%andspan+.08%arenotindependentlyvalidatedties. Joint32cursorreducesqueuebutP99worsensandPFC2→26. Four-casecursorregressionsincludeSharedRingP99slow+~9.5%,Alltoallmean+~.43%; Joint32cursorAnalyticsP99slow+~2.3%,Alltoallqueue+~5.3%. Seecomparison.jsonexactvalues. CandidateuniversaladvantageNOTachieved.

Next useful actions (hypotheses, not implemented):
1. Investigatehowfairnessturngranularityinteractswith8-packetACKbatches. OnefairpacketcanleavepartialACKbatchesunderSRPT. AcappedfairnessturnthatcompletesabatchcouldkeepACKefficiencyandself-clockingwithouttimer-generatedfeedbackbursts. Preserveeligibility/pacing andavoidpriorityinversion; testactualschedulerfirst, matchedfullDP2thenalloriginalregressions. Do notjustsweeplargerquantums.
2. Alternativelylookatlong-flowfabricfeedbackandrecovery: highgain+deadlineimproveslatencybutPFC/queueexplode. Existingadaptive_target_max_bdps=8excludesDP2elephants; applyingqueue-awaretargetstolongflowsisaplausiblecausalcontrolonlyafterfreezingthecombinedmechanism. Priorcampaignsrejectedbroadretuning,readpreviousreportsbeforeduplicating.
3. Confirm/fixHomaRESENDiterationdeterminismusingstablewireflowidentity, withsame-buildrepeatandobservationpairs. Preserveallbaselineresults; noselectivebaselineweakening.
4. Avoidclaimingtheseunitcorrectnessfixesareuniversalperformancewins. Keeponeglobalcandidateandalloriginalfigures/fourbaselinesinfinalindependentconfirmation; preservefailed/rejectedoutcomes. No newholdoutuntilviablecandidatefrozen.

Evidence: REPORT.zh.md,analysis.json,diagnostic_analysis.json,comparison.json,validation_checks.json,raw_index.json,tests.json,visual_review.json,harness_snapshots/. Source/build/input/harness/archiveintegrityverified,8figuresinspected. Originalguard650811aandits2useruntrackedartifactdirsuntouched. No .tex edits.
