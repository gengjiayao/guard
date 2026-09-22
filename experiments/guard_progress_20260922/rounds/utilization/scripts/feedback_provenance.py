from pathlib import Path
R=Path('/home/gengjiayao/ict/guard-utilfeedback')
def edit(name,old,new):
 p=R/name;s=p.read_text();assert old in s,(name,old);p.write_text(s.replace(old,new,1))
h='src/point-to-point/model/rdma-queue-pair.h';qc='src/point-to-point/model/rdma-queue-pair.cc';c='src/point-to-point/model/rdma-hw.cc';sim='scratch/network-load-balance.cc'
edit(h,'    bool m_guard_util_report_ready;','    uint32_t m_guard_util_issued_generation, m_guard_util_high_first_generation, m_guard_util_report_generation;\n    uint64_t m_guard_util_last_issued_rate;\n    bool m_guard_util_report_ready;')
edit(qc,'    m_guard_util_report_ready = false;','    m_guard_util_issued_generation = m_guard_util_high_first_generation = m_guard_util_report_generation = 0;\n    m_guard_util_last_issued_rate = 0;\n    m_guard_util_report_ready = false;')
edit(c,'        rx_qp->m_guard_util_report_rate_bps = reported_rate_bps;','        rx_qp->m_guard_util_report_generation = ch.ack.irnNack;\n        rx_qp->m_guard_util_report_rate_bps = reported_rate_bps;')
edit(c,'        report.SetIrnNack(0);','        // This field is unused in CAP_REPORT frames; echo the wire grant nonce.\n        report.SetIrnNack(qp->m_guard_last_grant_generation);')
edit(c,'        if (flow->m_guard_util_report_ready && flow->m_guard_util_report_rate_bps >= line * 90 / 100 &&','''        if (flow->m_guard_util_high_first_generation > 0 &&
            flow->m_guard_util_report_generation >= flow->m_guard_util_high_first_generation &&
            flow->m_guard_util_report_generation <= flow->m_guard_util_issued_generation &&
            flow->m_guard_util_report_ready && flow->m_guard_util_report_rate_bps >= line * 90 / 100 &&''')
edit(c,'    m_guardRateGrantsSent++;','''    if (m_guardUtilizationCapReports) {
        NS_ABORT_MSG_IF(generation != 0 || ack_required, "utilization probe cannot share reliable grant sequencing");
        NS_ABORT_MSG_IF(rx_qp->m_guard_util_issued_generation == std::numeric_limits<uint32_t>::max(),
                        "utilization grant nonce exhausted");
        generation = ++rx_qp->m_guard_util_issued_generation;
        uint64_t rate = static_cast<uint64_t>(rate_data) * 1000000ULL;
        uint64_t high = m_nic[GetNicIdxOfRxQp(rx_qp)].dev->GetDataRate().GetBitRate() * 90 / 100;
        if (rate < high) rx_qp->m_guard_util_high_first_generation = 0;
        else if (rx_qp->m_guard_util_last_issued_rate < high)
            rx_qp->m_guard_util_high_first_generation = generation;
        rx_qp->m_guard_util_last_issued_rate = rate;
    }
    m_guardRateGrantsSent++;''')
edit(c,'            GuardUtilizationFabricReady() ? 1 : 0);','''            GuardUtilizationFabricReady() ? 1 : 0);
    fprintf(file, ",%u,%u,%u", qp == NULL ? 0 : qp->m_guard_util_report_generation,
            qp == NULL ? 0 : qp->m_guard_util_high_first_generation,
            qp == NULL ? 0 : qp->m_guard_util_issued_generation);''')
edit(sim,'utilization_report_time_ns,utilization_fabric_ready");','utilization_report_time_ns,utilization_fabric_ready,utilization_report_generation,utilization_high_first_generation,utilization_issued_generation");')
