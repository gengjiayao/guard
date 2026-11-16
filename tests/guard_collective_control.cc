#include "ns3/rdma-hw.h"
#include "ns3/rdma-queue-pair.h"
#include "ns3/boolean.h"
#include "ns3/double.h"
#include "ns3/uinteger.h"
#include <algorithm>
#include <cassert>
#include <iostream>
#include <set>
#include <vector>
using namespace ns3;

int main() {
    assert(RdmaHw::ComputeGuardAckBatch(52000,1000,8,0)==8);
    assert(RdmaHw::ComputeGuardAckBatch(52000,1000,8,.125)==6);
    assert(RdmaHw::ComputeGuardAckBatch(104000,1000,8,.125)==8);
    assert(RdmaHw::ComputeGuardAckBatch(4000,1000,8,.125)==1);
    for (uint64_t bdp=1;bdp<250000;bdp+=127) {
        uint32_t batch=RdmaHw::ComputeGuardAckBatch(bdp,1000,8,.125);
        assert(batch>=1 && batch<=8);
        assert(batch==1 || batch*1000<=bdp*.125);
    }
    // A delayed flow may recover bounded missed service. Long idle periods
    // never create an unbounded burst and zero credit preserves old pacing.
    Time now=NanoSeconds(10000), packet=NanoSeconds(1000), budget=NanoSeconds(2000);
    assert(RdmaHw::ComputeGuardPacingDeadline(now,NanoSeconds(0),packet,NanoSeconds(0))==now+packet);
    Time deadline=RdmaHw::ComputeGuardPacingDeadline(now,NanoSeconds(0),packet,budget);
    assert(deadline==NanoSeconds(9000));
    unsigned burst=1;
    while(deadline<=now && burst<100) {
        deadline=RdmaHw::ComputeGuardPacingDeadline(now,deadline,packet,budget);++burst;
    }
    assert(burst==3 && deadline>now); // rate*credit plus one packet maximum
    for (int idle=0;idle<=100000;idle+=127) {
        Time d=RdmaHw::ComputeGuardPacingDeadline(now,NanoSeconds(10000-idle),packet,budget);
        assert(d>=now-budget+packet && d<=now+packet);
    }
    auto hw=CreateObject<RdmaHw>();hw->m_cc_mode=11;
    auto qp=CreateObject<RdmaQueuePair>(3,Ipv4Address(1),Ipv4Address(2),1,2);
    hw->m_guardTailCongestionGate=true;hw->m_guardTailSafeSamples=2;
    qp->m_guard_tail_bypass=true;qp->m_guard_tail_safe_samples=2;
    assert(hw->UsesGuardTailBypass(qp));
    qp->m_guard_tail_safe_samples=0;assert(!hw->UsesGuardTailBypass(qp));
    // A congestion spike arriving between full RTT updates must revoke a
    // previously granted bypass; a burst of fast safe ACKs cannot re-arm it.
    hw->m_guardQueueBudgetBdps=.5;hw->m_guardTailSafeRatio=.9;
    hw->UpdateGuardTailSafety(qp,.1,true);
    assert(!hw->UsesGuardTailBypass(qp));
    hw->UpdateGuardTailSafety(qp,.1,true);
    assert(hw->UsesGuardTailBypass(qp));
    hw->UpdateGuardTailSafety(qp,.6,false);
    assert(!hw->UsesGuardTailBypass(qp));
    for (unsigned i=0;i<100;++i)hw->UpdateGuardTailSafety(qp,.1,false);
    assert(!hw->UsesGuardTailBypass(qp));
    hw->UpdateGuardTailSafety(qp,.1,true);
    hw->UpdateGuardTailSafety(qp,.1,true);
    assert(hw->UsesGuardTailBypass(qp));
    hw->m_guardTailCongestionGate=false;
    hw->UpdateGuardTailSafety(qp,100,false);
    assert(qp->m_guard_tail_safe_samples==2); // disabled policy unchanged

    for (unsigned count=2;count<=32;++count) for (double fraction : {0.0,.1,1.0}) {
        auto allocator=CreateObject<RdmaHw>();
        allocator->m_guardReceiverConcurrency=1;
        allocator->m_guardMinShareFraction=fraction;
        allocator->m_guardConcurrencyMinBdps=0;
        allocator->m_guardReceiverPhaseOrder=true;
        std::vector<Ptr<RdmaRxQueuePair>> flows;
        for (unsigned i=0;i<count;++i) {
            auto flow=CreateObject<RdmaRxQueuePair>();flow->sip=1000;flow->dip=2000+i;
            flow->m_guard_flow_size=1000000+i*10000;flow->ReceiverNextExpectedSeq=i*1000;
            flow->m_base_rtt_sec=8.32e-6;flow->m_flow_id=i;
            flows.push_back(flow);allocator->m_rate_flow_ctl_set.insert(PeekPointer(flow));
        }
        auto targets=allocator->ComputeGuardBaseTargets(100000000000ULL);
        uint64_t sum=0,floor=fraction*(100000000000ULL/count);
        for (auto &item : targets) {assert(item.second>=floor);sum+=item.second;}
        assert(sum<=100000000000ULL);
        allocator->m_rate_flow_ctl_set.clear();
        for (auto it=flows.rbegin();it!=flows.rend();++it)allocator->m_rate_flow_ctl_set.insert(PeekPointer(*it));
        uint32_t previous_id=0;bool first=true;
        for (auto *flow : allocator->m_rate_flow_ctl_set) {
            assert(first || flow->m_flow_id>previous_id);
            previous_id=flow->m_flow_id;first=false;
        }
        auto reordered=allocator->ComputeGuardBaseTargets(100000000000ULL);
        for (auto &item : targets)assert(item.second==reordered[item.first]);
    }
    auto duplex=CreateObject<RdmaHw>();duplex->m_guardDuplexAdaptive=true;
    assert(!duplex->GuardHasMultipleActiveDestinations());
    for (unsigned i=0;i<2;++i) {
        auto tx=CreateObject<RdmaQueuePair>(3,Ipv4Address(1),Ipv4Address(2+i),1,2);
        tx->m_size=1000000;duplex->m_qpMap[i]=tx;
    }
    assert(duplex->GuardHasMultipleActiveDestinations());
    duplex->m_qpMap[1]->snd_una=1000000;
    assert(!duplex->GuardHasMultipleActiveDestinations());
    std::vector<Ptr<RdmaRxQueuePair>> duplex_rx;
    for (unsigned i=0;i<2;++i) {
        auto rx=CreateObject<RdmaRxQueuePair>();rx->sip=1;rx->dip=2+i;
        duplex_rx.push_back(rx);duplex->m_rate_flow_ctl_set.insert(PeekPointer(rx));
    }
    assert(!duplex->GuardHasCompetingSenders()); // one outbound peer remains
    duplex->m_guardDuplexSizeRatio=4.0;
    duplex_rx[0]->m_guard_flow_size=1048576;
    duplex_rx[1]->m_guard_flow_size=4194304;
    assert(duplex->GuardHasCompetingSenders());
    duplex_rx[1]->m_guard_flow_size=3145728;
    assert(!duplex->GuardHasCompetingSenders());
    duplex->m_guardDuplexSizeRatio=0.0;

    duplex->m_qpMap[0]->snd_una=1000000;
    assert(duplex->GuardHasCompetingSenders());
    duplex->m_guardDuplexCohortDrain=true;
    duplex->m_qpMap[0]->snd_una=0;
    duplex->RefreshGuardDuplexCohort();
    assert(duplex->m_guardDuplexCohortActive);
    duplex->m_qpMap[0]->snd_una=1000000;
    duplex->RefreshGuardDuplexCohort();
    assert(!duplex->GuardHasCompetingSenders()); // receives still draining
    duplex->m_rate_flow_ctl_set.clear();
    duplex->RefreshGuardDuplexCohort();
    assert(!duplex->m_guardDuplexCohortActive);
    assert(duplex->m_guardDuplexCohortActivations==1);
    std::set<uint32_t> selected_senders, first_grant_senders;
    for (uint32_t receiver=100;receiver<108;++receiver) {
        auto allocator=CreateObject<RdmaHw>();allocator->m_guardReceiverConcurrency=1;
        allocator->m_guardMinShareFraction=.1;allocator->m_guardConcurrencyMinBdps=0;
        allocator->m_guardReceiverPhaseOrder=true;
        std::vector<Ptr<RdmaRxQueuePair>> flows;
        for (uint32_t sender=100;sender<108;++sender) if(sender!=receiver) {
            auto flow=CreateObject<RdmaRxQueuePair>();flow->sip=receiver;flow->dip=sender;
            flow->m_guard_flow_size=1048576;flow->ReceiverNextExpectedSeq=1000;
            flow->m_base_rtt_sec=8.32e-6;flow->m_flow_id=sender;
            flows.push_back(flow);allocator->m_rate_flow_ctl_set.insert(PeekPointer(flow));
        }
        first_grant_senders.insert((*allocator->m_rate_flow_ctl_set.begin())->dip);
        auto rates=allocator->ComputeGuardBaseTargets(100000000000ULL);
        auto best=std::max_element(rates.begin(),rates.end(),[](const std::pair<RdmaRxQueuePair* const,uint64_t>&a,const std::pair<RdmaRxQueuePair* const,uint64_t>&b){return a.second<b.second;});
        selected_senders.insert(best->first->dip);
    }
    assert(selected_senders.size()==8);
    assert(first_grant_senders.size()==8);
    std::cout<<"PASS bounded pacing and ACK clock, tail safety, capacity/fairness, deterministic phase order and duplex cohort draining\n";
}
