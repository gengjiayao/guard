# Full-objective continuation

Goal ACTIVE. User requires every original paper figure against HPCC,Homa,DCQCN,TIMELY under a single final configuration, original inputs and all relevant metrics, with independently confirmed advantages or genuine ties. This development campaign uses already-observed seed301 only. No paper/Overleaf promotion and no independent seeds. Do not mark complete based on unit fixes or isolated gains.

Frozen sources:
- guard-homastable d6d646f: deterministic Homa RESEND batch sorting by message ID and endpoints; default on. Diagnostic hash bucket representation control default0, with11/257 probes. Timers/ranges/priority/grant semantics unchanged. Four stable fullDP2 runs byte-identical across two repeats and altered buckets; legacy representation has three distinct FCT hashes. Baseline order was fixed before measurement, not selected by performance.
- guard-ackbatch d885002: optional guard_sender_ack_batch requires fair cursor. Keep successive fairness recipient until current cumulative ACK+8packet target reached; preserve configured64:1service, never block other eligible flows. Tests include partialbatch, pacing/PFC/window/completion/identity exclusions. No additional ACK timer. Same-build fullDP2 threeparents±batch, fourbaselines, tracepair; six original regression scenes.
- guard-servicebudget c3f7387: optional guard_sender_service_budget requires fair cursor. Existing consecutive-shortest quantum can starve a long flow when two short eligible identities alternate (actual650dequeues325/325/0). Count aggregate priority service, yield one packet after existingquantum64, reset only after choosing other eligible flow; no new tuning parameter. Actualfix320/320/10 with batch bothon/off; originalbatch/exclusiontests retained. FullDP2 threeparents±budget, twobudget+batchcombinations,Homa,onebudgettrace; sixoriginalregression scenes.

Do not edit or rebuild a frozen source while its simulations run. All rounds save manifest and exact driver snapshot. Prior campaigns and rejected profiles remain in ../guard_timeout_20260921/NEXT.md and the older evidence directories. Preserve originalguard650811a and its two user untracked artifact dirs.

Initial batch results are tradeoffs, not universal wins: Sharedcursor15.669mean/88.793P99ms/12.478queueus →batch16.072/93.676/12.649, althoughspan216.534→215.869ms. Joint32cursor16.450/58.835/24.707→batch16.258/55.827/26.944, PFC26→150. Sharedλ1cursor24.482/103.222/5.313→batch24.389/100.024/7.719, RTO3→4. Fulloriginal1280flowDP2 throughout. Guardbatch cannot be promoted globally.

All original figure families remain required: workloadmean/tails; AliStorage30/50 every size bin; fabric,receiver2,hybrid; strictcomponentablations;OFLM;fairness;Alltoall/fullDP2span,CDF,threequeueranks;Ring; supplementalseries/receiverwidth. New source effects on those not measured in this campaign are not automatically inherited as wins. Small development changes are not statistical ties.

Current evidence scripts: summarize.py validates allmanifest task terminalrecords and input/completionidentity/warmup; archive.py preserves allattempts; verify.py checks frozen source/build/topology/input/harness/rawarchives, sixstableHomaruns across3builds, fivecrossbuildGUARDcontrols and threeexacttracepairs. report.py+report_budget.py generate12figures and fullREPORT.zh.md. Diagnostics retain actual timeoutflightstates andserializedwirebytes includingheaders,excludingIFG. Maxtracecap300000, sample1ms; mandatorytimeout/completionrowsunsampled.

All70runs are now terminal, complete, zero drops, zero failedsimulation attempts. All source/build/input/harness/archive hashes verified.12figures inspected, including corrected Homa nativeRESEND and eventannotation panels. No live jobs; no paper edits or independentseeds. Currentturn made concrete progress; not a no-progress/blockerturn.

## Final measured service-budget effects

- budget_dp2_shared_cursor: mean15.668915ms,P9988.793154ms,span216.534419ms,queue12.478155us,RTO0,PFC0.
- budget_dp2_shared_budget: mean16.253867ms,P99108.957985ms,span216.196746ms,queue13.049746us,RTO0,PFC0.
- budget_dp2_shared_budget_batch: mean16.106172ms,P9995.246897ms,span215.888231ms,queue12.731955us,RTO0,PFC0.
- budget_dp2_joint32_cursor: mean16.449827ms,P9958.835300ms,span216.961442ms,queue24.707438us,RTO0,PFC26.
- budget_dp2_joint32_budget: mean16.357484ms,P9956.171553ms,span217.264228ms,queue26.504447us,RTO0,PFC0.
- budget_dp2_shared_l10_cursor: mean24.482303ms,P99103.222295ms,span227.557713ms,queue5.313445us,RTO3,PFC0.
- budget_dp2_shared_l10_budget: mean25.567084ms,P99105.515674ms,span226.813901ms,queue2.469959us,RTO0,PFC0.
- budget_dp2_shared_l10_budget_batch: mean25.360910ms,P9999.491368ms,span226.011947ms,queue2.403396us,RTO0,PFC0.

Sharedλ1budget fixes3observedpartialACKtimeouts→0 and lowersqueue5.313→2.470us, butmean24.482→25.567ms andP99103.222→105.516ms worsen. Joint32budgetmean16.450→16.357/P9958.835→56.172/PFC26→0, butqueue24.707→26.504us andspan216.961→217.264ms worsen. SharedbudgetP99gets108.958ms. No universalwin. Batchbudgetcombination doesnoteliminatetradeoffs.

Six-casebudgetregressions: SharedRingmean−2.64%,P99slow−5.82%,span−1.37%,queue−1.74%; SharedAlltoallmean+4.82%,queue+12.97%; Joint32Alltoallmean+4.91%,queue+12.20%. Storage50Sharedqueue−15.16%,span−1.95%, butP99slow+0.38%, several size-bin tails change. Usebudget_comparison.json andallbinrecordsfor exactvalues; nonearevalidatedties.

Three exacttracepairs: Sharedλ1cursor3timeouts with4000/7000/3000outstandingbytes; batch4with4000/7000/4000/2000; budget0. Everytracehas1280matchedcompletionevents, nocapomissions. NativeHomaRESEND10618,replayedcompletionnotices189; genericRTO0isnotnorecovery. SixstableHomafullDP2runs across3builds haveexactFCT+allmetrics equality. FivecrossbuildGUARDcontrols verifiedexact.

Next useful work: use the eliminated partialACKtimeout mechanism as a correctness repair, while avoiding the unconditional fair-service priority cost on short Alltoall traffic. A service-age condition derived from actual outstanding partialACK state and existing feedback/recovery timing is a possible focused experiment, not yet implemented; do not sweep arbitraryper-scenethresholds. Separately, highgainShared stillhaslong tailswithoutRTO, so starvation doesnotexplainalltails. Trace long-flowfabriccap and actualremainingwork before anothercontrolchange. All-flowadaptive_target_max_bdps=0wasalreadyrejected in guard_tailtrace campaign (Shared16.855mean/87.129P99/11.308queue,Startup16.592/103.424/10.989), so do not repeat it blindly. Full original scope and fourbaseline independentconfirmation remain necessary before anypromotion.
