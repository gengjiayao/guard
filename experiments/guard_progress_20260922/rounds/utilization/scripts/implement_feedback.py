"""Apply explicit feedback-gated entry as a separate default-off experiment."""
from pathlib import Path
R=Path('/home/gengjiayao/ict/guard-utilfeedback')
def edit(name,old,new,count=1):
 p=R/name;s=p.read_text();assert s.count(old)>=count,(name,old);p.write_text(s.replace(old,new,count))
h='src/point-to-point/model/rdma-hw.h';c='src/point-to-point/model/rdma-hw.cc';qh='src/point-to-point/model/rdma-queue-pair.h';qc='src/point-to-point/model/rdma-queue-pair.cc';header='src/point-to-point/model/qbb-header.h';impl='src/point-to-point/model/qbb-header.cc';run='run.py';sim='scratch/network-load-balance.cc'
edit(header,'FLAG_GUARD_CAP_REPORT = 2','FLAG_GUARD_CAP_REPORT = 2,\n      FLAG_GUARD_UTILIZATION_READY = 3')
edit(header,'  void SetGuardCapReport();','  void SetGuardCapReport();\n  void SetGuardUtilizationReady(bool ready);')
edit(impl,'\tvoid qbbHeader::SetIntHeader', '''    void qbbHeader::SetGuardUtilizationReady(bool ready) {
        if (ready) flags |= 1 << FLAG_GUARD_UTILIZATION_READY;
        else flags &= ~(1 << FLAG_GUARD_UTILIZATION_READY);
    }
\tvoid qbbHeader::SetIntHeader''')
edit(qh,'    bool m_guard_has_cap_report;','    bool m_guard_has_cap_report;\n    uint64_t m_guard_util_high_grant_start_ns;')
edit(qc,'    m_guard_has_cap_report = false;','    m_guard_has_cap_report = false;\n    m_guard_util_high_grant_start_ns = 0;')
edit(qh,'    uint64_t m_guard_spillover_reported_cap_bps;','    bool m_guard_util_report_ready;\n    uint64_t m_guard_util_report_rate_bps;\n    Time m_guard_util_report_time;\n    uint64_t m_guard_spillover_reported_cap_bps;')
edit(qc,'    m_guard_spillover_reported_cap_bps = 0;','    m_guard_util_report_ready = false;\n    m_guard_util_report_rate_bps = 0;\n    m_guard_util_report_time = Time(0);\n    m_guard_spillover_reported_cap_bps = 0;')
edit(h,'    bool m_guardUtilizationConcurrency;','    bool m_guardUtilizationConcurrency;\n    bool m_guardUtilizationCapReports, m_guardUtilizationFabricGate;\n    uint64_t m_guardUtilizationBlocked;\n    bool GuardUtilizationFabricReady() const;')
edit(c,'            .AddAttribute("GuardUtilizationConcurrency",','''            .AddAttribute("GuardUtilizationCapReports",
                          "Transmit real fresh fabric-readiness reports for high-grant horizon flows",
                          BooleanValue(false), MakeBooleanAccessor(&RdmaHw::m_guardUtilizationCapReports),
                          MakeBooleanChecker())
            .AddAttribute("GuardUtilizationFabricGate",
                          "Require a fresh positive report from the high-grant primary before widening",
                          BooleanValue(false), MakeBooleanAccessor(&RdmaHw::m_guardUtilizationFabricGate),
                          MakeBooleanChecker())
            .AddAttribute("GuardUtilizationConcurrency",''')
edit(c,'    m_guardUtilizationWide = false;','    m_guardUtilizationBlocked = 0;\n    m_guardUtilizationWide = false;')
edit(c,'    qp->hp.m_grantRate = curRate;','''    if (m_guardUtilizationCapReports) {
        uint64_t threshold = qp->m_max_rate.GetBitRate() * 90 / 100;
        if (curRate.GetBitRate() < threshold) qp->m_guard_util_high_grant_start_ns = 0;
        else if (qp->m_guard_util_high_grant_start_ns == 0)
            qp->m_guard_util_high_grant_start_ns = Simulator::Now().GetNanoSeconds();
    }
    qp->hp.m_grantRate = curRate;''')
edit(c,'int RdmaHw::ReceiveGuardCapReport(Ptr<Packet> /*p*/, CustomHeader &ch)', 'int RdmaHw::ReceiveGuardCapReport(Ptr<Packet> p, CustomHeader &ch)')
edit(c,'    if (m_guardElephantCapSpillover || m_guardCapTriggeredRefresh) {','''    if (m_guardUtilizationCapReports) {
        rx_qp->m_guard_util_report_ready =
            ((ch.ack.flags >> qbbHeader::FLAG_GUARD_UTILIZATION_READY) & 1) != 0 && !fabric_bound;
        rx_qp->m_guard_util_report_rate_bps = reported_rate_bps;
        rx_qp->m_guard_util_report_time = now;
        uint64_t line = 0;
        for (auto const &nic : m_nic) if (nic.dev != NULL) line = nic.dev->GetDataRate().GetBitRate();
        TraceGuardGrant(rx_qp, "utilization_report", rx_qp->m_guard_util_report_ready ? "ready" : "not_ready",
            m_rate_flow_ctl_set.size(), line, rx_qp->m_guard_grant_rate_bps,
            rx_qp->ReceiverNextExpectedSeq, p->GetSize(), 0, 0, false, 0);
    }
    if (m_guardElephantCapSpillover || m_guardCapTriggeredRefresh) {''')
edit(c,'         !m_guardCapTriggeredRefresh) ||','         !m_guardCapTriggeredRefresh && !m_guardUtilizationCapReports) ||')
edit(c,'    Time now = Simulator::Now();\n    Time interval = NanoSeconds(std::max<uint64_t>(1, qp->m_baseRtt));','''    if (m_guardUtilizationCapReports && !m_guardCapAwareReclaim &&
        !m_guardElephantCapSpillover && !m_guardCapTriggeredRefresh) {
        // Only a near-line-rate primary can authorize entry. A deferred flow's
        // unbound-at-floor feedback is not evidence of spare path capacity.
        if (bdp_bytes == 0 || qp->m_size <= m_guardConcurrencyMinBdps * bdp_bytes ||
            qp->m_size > m_guardSchedulingHorizonBdps * bdp_bytes ||
            qp->hp.m_grantRate.GetBitRate() < qp->m_max_rate.GetBitRate() * 90 / 100) return;
    }
    Time now = Simulator::Now();
    Time interval = NanoSeconds(std::max<uint64_t>(1, qp->m_baseRtt));''')
edit(c,'    report.SetGuardFabricBound(fabric_bound);','''    report.SetGuardFabricBound(fabric_bound);
    if (m_guardUtilizationCapReports) {
        uint64_t time_ns = now.GetNanoSeconds();
        uint64_t feedback = qp->m_guard_last_full_feedback_ns;
        uint64_t started = qp->m_guard_util_high_grant_start_ns;
        bool ready = !fabric_bound && started > 0 &&
            feedback >= started + qp->m_baseRtt && feedback <= time_ns &&
            time_ns - feedback <= qp->m_baseRtt &&
            qp->m_rate.GetBitRate() >= qp->m_max_rate.GetBitRate() * 90 / 100;
        report.SetGuardUtilizationReady(ready);
        report.SetIrnNack(0);
        report.SetIrnNackSize(0);
    }''')
edit(c,'bool RdmaHw::GuardUtilizationEligible() const {','''bool RdmaHw::GuardUtilizationFabricReady() const {
    uint64_t line = 0;
    for (auto const &nic : m_nic) if (nic.dev != NULL) line = nic.dev->GetDataRate().GetBitRate();
    for (auto *flow : m_rate_flow_ctl_set) {
        if (flow->m_guard_grant_rate_bps < line * 90 / 100) continue;
        uint64_t rtt = flow->m_base_rtt_sec > 0
            ? static_cast<uint64_t>(flow->m_base_rtt_sec * 1e9 + 0.5) : 8320;
        if (flow->m_guard_util_report_ready && flow->m_guard_util_report_rate_bps >= line * 90 / 100 &&
            !flow->m_guard_util_report_time.IsZero() &&
            Simulator::Now() - flow->m_guard_util_report_time <= NanoSeconds(2 * rtt)) return true;
    }
    return false;
}

bool RdmaHw::GuardUtilizationEligible() const {''')
edit(c,'        m_guardUtilizationWide = true; ++m_guardUtilizationPromotions; changed = true;','''        if (!m_guardUtilizationFabricGate || GuardUtilizationFabricReady()) {
            m_guardUtilizationWide = true; ++m_guardUtilizationPromotions; changed = true;
        } else ++m_guardUtilizationBlocked;''')
edit(c,'            m_guardUtilizationLowWindows, m_guardUtilizationHighWindows);','''            m_guardUtilizationLowWindows, m_guardUtilizationHighWindows);
    fprintf(file, ",%u,%lu,%lu,%u", qp != NULL && qp->m_guard_util_report_ready ? 1 : 0,
            qp == NULL ? 0 : qp->m_guard_util_report_rate_bps,
            qp == NULL ? 0 : static_cast<uint64_t>(qp->m_guard_util_report_time.GetNanoSeconds()),
            GuardUtilizationFabricReady() ? 1 : 0);''')
edit(sim,'utilization_low_windows,utilization_high_windows");','utilization_low_windows,utilization_high_windows,utilization_report_ready,utilization_report_rate_bps,utilization_report_time_ns,utilization_fabric_ready");')
for stem in ['cap_reports','fabric_gate']:
 camel='CapReports' if stem=='cap_reports' else 'FabricGate';option='guard_utilization_'+stem;upper=option.upper()
 edit(run,'GUARD_UTILIZATION_CONCURRENCY {guard_utilization_concurrency}',f'{upper} {{{option}}}\nGUARD_UTILIZATION_CONCURRENCY {{guard_utilization_concurrency}}')
 edit(run,"    parser.add_argument('--guard_utilization_concurrency'",f"    parser.add_argument('--{option}', type=int, choices=(0,1), default=0)\n    parser.add_argument('--guard_utilization_concurrency'")
 edit(run,'                                        guard_utilization_concurrency=args.guard_utilization_concurrency,',f'                                        {option}=args.{option},\n                                        guard_utilization_concurrency=args.guard_utilization_concurrency,')
 edit(sim,'bool guard_utilization_concurrency = false;',f'bool {option} = false;\nbool guard_utilization_concurrency = false;')
 edit(sim,'            } else if (key.compare("GUARD_UTILIZATION_CONCURRENCY") == 0) {',f'            }} else if (key.compare("{upper}") == 0) {{\n                conf >> {option};\n            }} else if (key.compare("GUARD_UTILIZATION_CONCURRENCY") == 0) {{')
 edit(sim,'            rdmaHw->SetAttribute("GuardUtilizationConcurrency",',f'            rdmaHw->SetAttribute("GuardUtilization{camel}", BooleanValue({option}));\n            rdmaHw->SetAttribute("GuardUtilizationConcurrency",')
edit(run,'    if args.guard_utilization_concurrency and (','''    if args.guard_utilization_fabric_gate and (not args.guard_utilization_cap_reports or not args.guard_utilization_concurrency):
        raise ValueError('fabric gate requires utilization concurrency and cap reports')
    if (args.guard_utilization_concurrency or args.guard_utilization_cap_reports) and (''')
edit(sim,'    if (guard_utilization_concurrency &&','''    if (guard_utilization_fabric_gate && (!guard_utilization_cap_reports || !guard_utilization_concurrency)) {
        std::cerr << "Fabric gate requires utilization concurrency and cap reports\\n";
        return 1;
    }
    if ((guard_utilization_concurrency || guard_utilization_cap_reports) &&''')
edit(sim,'        fprintf(guard_stats_output, "guard_utilization_width node', '''        fprintf(guard_stats_output, "guard_utilization_feedback node %u reports %u gate %u blocked %lu\\n",
                i, guard_utilization_cap_reports ? 1 : 0, guard_utilization_fabric_gate ? 1 : 0,
                hw->m_guardUtilizationBlocked);
        fprintf(guard_stats_output, "guard_utilization_width node''')
