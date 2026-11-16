#include "ns3/qbb-net-device.h"
#include "ns3/rdma-queue-pair.h"
#include "ns3/int-header.h"
#include <cassert>
#include <iostream>
using namespace ns3;
static Ptr<RdmaQueuePair> make(unsigned pg,uint64_t bytes) {
 auto q=CreateObject<RdmaQueuePair>(pg,Ipv4Address("10.0.0.1"),Ipv4Address("10.0.0.2"),1000+pg,2000);
 q->SetSize(bytes);q->SetWin(100000);q->SetVarWin(false);q->SetBaseRtt(8000);
 q->m_max_rate=DataRate(100000000000ULL);q->m_guard_sender_srpt=true;
 q->m_guard_sender_srpt_max_bdps=16;q->m_flow_id=pg;
 return q;
}
int main() {
 IntHeader::mode=0;auto eq=CreateObject<RdmaEgressQueue>();eq->m_qpGrp=CreateObject<RdmaQueuePairGroup>();
 auto a=make(1,2000000),b=make(2,10000000);eq->m_qpGrp->AddQp(a);eq->m_qpGrp->AddQp(b);
 bool paused[8]={false};
 // The first RR-ready entry is b; neither message has bounded work.
 assert(eq->GetNextQindex(paused)==1);
 a->m_size=500000;assert(eq->GetNextQindex(paused)==0);
 // Eligibility remains subject to original PFC, pacing and byte-window gates.
 paused[1]=true;assert(eq->GetNextQindex(paused)==1);paused[1]=false;
 a->m_nextAvail=NanoSeconds(1000);assert(eq->GetNextQindex(paused)==1);a->m_nextAvail=Time(0);
 a->snd_nxt=100000;assert(eq->GetNextQindex(paused)==1);a->snd_nxt=0;
 a->m_guard_wait_first_grant=true;a->m_guard_first_grant_win=1000;a->snd_nxt=1000;
 assert(eq->GetNextQindex(paused)==1);a->m_guard_wait_first_grant=false;a->snd_nxt=0;
 paused[1]=paused[2]=true;assert(eq->GetNextQindex(paused)==-1024);paused[1]=paused[2]=false;
 // The short-work classification uses each path's own BDP.
 a->m_size=2000000;a->m_baseRtt=16000;assert(eq->GetNextQindex(paused)==0);
 a->m_baseRtt=8000;assert(eq->GetNextQindex(paused)==1);
 // Zero cutoff preserves unrestricted SRPT; disabling SRPT preserves RR.
 a->m_guard_sender_srpt_max_bdps=b->m_guard_sender_srpt_max_bdps=0;
 assert(eq->GetNextQindex(paused)==0);
 assert(RdmaEgressQueue::ComputeGuardSenderCutoff(32,16,{2,3,10000})==32);
 assert(RdmaEgressQueue::ComputeGuardSenderCutoff(32,16,{16,24,32})==20);
 assert(RdmaEgressQueue::ComputeGuardSenderCutoff(32,16,{32,64,96})==8);
 assert(RdmaEgressQueue::ComputeGuardSenderCutoff(2,1,{4,10})==1);
 assert(RdmaEgressQueue::ComputeGuardSenderCutoff(32,0,{1000,2000})==32);
 assert(RdmaEgressQueue::ComputeGuardSenderCutoff(32,16,{})==32);
 a->m_guard_sender_srpt_max_bdps=b->m_guard_sender_srpt_max_bdps=32;
 a->m_guard_sender_srpt_cohort_bdps=b->m_guard_sender_srpt_cohort_bdps=16;
 // A long cohort narrows bounded priority to 8 BDPs, retaining RR for both.
 assert(eq->GetNextQindex(paused)==1);
 // A draining tail regains priority without reclassifying its original work.
 a->snd_una=a->snd_nxt=1500000;assert(eq->GetNextQindex(paused)==0);
 paused[1]=true;assert(eq->GetNextQindex(paused)==1);paused[1]=false;
 a->snd_una=a->snd_nxt=1000000;b->snd_una=b->snd_nxt=8000000;
 assert(eq->GetNextQindex(paused)==1); // Original long cohort stays classified while both drain.
 a->snd_una=a->snd_nxt=0;b->snd_una=b->snd_nxt=0;
 // A bounded cohort retains the full 32-BDP priority range.
 b->m_size=1000000;eq->m_rrlast=1;assert(eq->GetNextQindex(paused)==1);
 b->m_size=10000000;eq->m_rrlast=0;
 a->m_guard_sender_srpt_cohort_bdps=b->m_guard_sender_srpt_cohort_bdps=0;
 a->m_guard_sender_srpt=b->m_guard_sender_srpt=false;assert(eq->GetNextQindex(paused)==1);
 std::cout<<"PASS: cohort endpoints, outlier robustness, stable drain classification, short-work protection, long-work rotation and all original eligibility gates\n";
}
