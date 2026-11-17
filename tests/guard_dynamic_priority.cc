#include "ns3/rdma-hw.h"
#include "ns3/rdma-queue-pair.h"
#include "ns3/custom-header.h"
#include "ns3/broadcom-egress-queue.h"
#include <cassert>
#include <iostream>
using namespace ns3;
static CustomHeader header(Ptr<Packet> p) {
 CustomHeader h(CustomHeader::L2_Header|CustomHeader::L3_Header|CustomHeader::L4_Header);
 p->PeekHeader(h);return h;
}
static Ptr<RdmaQueuePair> make(bool enabled) {
 auto q=CreateObject<RdmaQueuePair>(5,Ipv4Address("10.0.0.1"),Ipv4Address("10.0.0.2"),1000,2000);
 q->SetSize(8000);q->SetWin(100000);q->SetVarWin(false);q->SetBaseRtt(80);
 q->m_max_rate=DataRate(100000000000ULL);q->m_guard_dynamic_priority=enabled;q->m_guard_schedule_pg=5;
 return q;
}
int main() {
 auto hw=CreateObject<RdmaHw>();hw->m_cc_mode=11;hw->m_mtu=1000;
 hw->m_guardTailBypass=false;hw->m_guardDynamicPriority=true;hw->m_guardScheduledSizePriority=true;
 auto q=make(true);auto p=hw->GetNxtPacket(q);auto h=header(p);
 assert(h.udp.pg==5 && h.GetGuardScheduleClass()==5);
 assert(h.m_tos & CustomHeader::GUARD_SCHEDULE_DRAIN_ACK);
 assert(q->m_guard_pending_pg==4 && q->m_guard_priority_barrier==1000);
 assert(q->IsWinBound());
 // Lost DATA / cumulative ACK cannot release a low-to-high transition.
 q->snd_una=999;assert(q->IsWinBound());q->snd_una=0;
 q->snd_nxt=0;assert(!q->IsWinBound());
 auto retry=header(hw->GetNxtPacket(q));
 assert(retry.GetGuardScheduleClass()==5 && (retry.m_tos & CustomHeader::GUARD_SCHEDULE_DRAIN_ACK));
 assert(hw->m_guardPriorityBarriers==1 && hw->m_guardPriorityPromotions==0);
 q->snd_una=1000;assert(!q->IsWinBound());
 auto promoted_packet=hw->GetNxtPacket(q);auto promoted=header(promoted_packet);assert(promoted.GetGuardScheduleClass()==4);
 assert(promoted.udp.pg==5 && q->m_pg==5 && hw->m_guardPriorityPromotions==1);
 // Service priority and lossless admission class must not be confused.
 auto queue=CreateObject<BEgressQueue>();queue->SetStrictPriority(true);queue->SetGuardSchedulePfc(true);
 queue->Enqueue(promoted_packet,4);bool paused[8]={false};paused[5]=true;
 assert(!queue->DequeueRR(paused));paused[5]=false;paused[4]=true;
 assert(queue->DequeueRR(paused)==promoted_packet);
 uint16_t last=4;
 while(q->GetBytesLeft()) {
  q->snd_una=q->snd_nxt;
  assert(!q->IsWinBound());auto next=header(hw->GetNxtPacket(q));
  assert(next.GetGuardScheduleClass()<=last && next.udp.pg==5);
  last=next.GetGuardScheduleClass();
 }
 assert(hw->m_guardPriorityPromotions>=3 && q->m_pg==5);
 // A protected top class must not add a new drain RTT to a one-BDP tail.
 hw->m_guardDynamicPriorityFloor=2;auto tail=make(true);tail->m_size=2500;tail->m_guard_schedule_pg=2;
 uint64_t barriers=hw->m_guardPriorityBarriers;
 while(tail->GetBytesLeft()) {
  tail->snd_una=tail->snd_nxt;auto h=header(hw->GetNxtPacket(tail));
  assert(h.GetGuardScheduleClass()==2 && h.udp.pg==5);
  assert(!tail->m_guard_pending_pg && !(h.m_tos & CustomHeader::GUARD_SCHEDULE_DRAIN_ACK));
 }
 assert(hw->m_guardPriorityBarriers==barriers);
 // Disabled flows retain their original header/queue behavior.
 auto off=make(false);auto old=header(hw->GetNxtPacket(off));
 assert(!old.HasGuardScheduleClass() && !(old.m_tos & CustomHeader::GUARD_SCHEDULE_DRAIN_ACK));
 assert(!off->m_guard_pending_pg && !off->m_guard_priority_barrier);
 std::cout<<"PASS: on-wire drain request, cumulative ACK barrier, retransmission eligibility, monotone promotion, immutable identity and disabled mode\n";
}
