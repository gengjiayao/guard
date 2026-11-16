#include "ns3/qbb-net-device.h"
#include "ns3/rdma-queue-pair.h"
#include "ns3/int-header.h"
#include <cassert>
#include <cmath>
#include <iostream>
using namespace ns3;
static Ptr<Packet> send(Ptr<RdmaQueuePair> q) {
 auto n=std::min<uint64_t>(1000,q->GetBytesLeft());q->snd_nxt+=n;q->snd_una=q->snd_nxt;
 return Create<Packet>(n);
}
static Ptr<RdmaQueuePair> make(unsigned pg,uint64_t rate) {
 auto q=CreateObject<RdmaQueuePair>(pg,Ipv4Address("10.0.0.1"),Ipv4Address("10.0.0.2"),1000+pg,2000);
 q->SetSize(100000000);q->SetWin(100000);q->SetVarWin(false);q->SetBaseRtt(8000);
 q->m_max_rate=DataRate(100000000000ULL);q->m_rate=DataRate(rate);
 q->m_guard_sender_srpt=true;q->m_guard_sender_srpt_max_bdps=1;
 q->m_guard_sender_rate_fair=true;q->m_flow_id=pg;return q;
}
int main() {
 IntHeader::mode=0;auto eq=CreateObject<RdmaEgressQueue>();eq->m_qpGrp=CreateObject<RdmaQueuePairGroup>();
 eq->m_rdmaGetNxtPkt=MakeCallback(&send);
 auto a=make(1,20000000000ULL),b=make(2,80000000000ULL);eq->m_qpGrp->AddQp(a);eq->m_qpGrp->AddQp(b);
 bool paused[8]={false};unsigned n[2]={0,0};
 for(unsigned i=0;i<1000;i++){int j=eq->GetNextQindex(paused);assert(j>=0);n[j]++;eq->DequeueQindex(j);}
 assert(std::abs((int)n[0]-200)<=2);assert(std::abs((int)n[1]-800)<=2);
 // Packetization and local calls cannot create rate credit before transmission.
 double finish=a->m_guard_sender_finish;eq->GetNextQindex(paused);eq->GetNextQindex(paused);assert(a->m_guard_sender_finish==finish);
 // A paused QP cannot retain an unbounded bank of service credit on re-entry.
 paused[1]=true;for(int i=0;i<500;i++){int j=eq->GetNextQindex(paused);assert(j==1);eq->DequeueQindex(j);}paused[1]=false;
 n[0]=n[1]=0;for(int i=0;i<100;i++){int j=eq->GetNextQindex(paused);n[j]++;eq->DequeueQindex(j);}assert(n[0]<25);
 // Receiver or passive-cap changes immediately change service weights.
 a->m_rate=DataRate(80000000000ULL);b->m_rate=DataRate(20000000000ULL);
 n[0]=n[1]=0;for(int i=0;i<1000;i++){int j=eq->GetNextQindex(paused);n[j]++;eq->DequeueQindex(j);}assert(std::abs((int)n[0]-800)<=3);
 // Bounded messages still have prompt service, subject to all original gates.
 a->m_size=a->snd_nxt+50000;assert(eq->GetNextQindex(paused)==0);
 paused[1]=true;assert(eq->GetNextQindex(paused)==1);paused[1]=false;
 a->m_nextAvail=NanoSeconds(1);assert(eq->GetNextQindex(paused)==1);a->m_nextAvail=Time(0);
 a->m_size=100000000;a->snd_nxt=a->snd_una+100000;assert(eq->GetNextQindex(paused)==1);
 // Disabled mode retains ordinary rotation for original long messages.
 a->m_size=100000000;a->snd_nxt=a->snd_una;
 a->m_guard_sender_rate_fair=b->m_guard_sender_rate_fair=false;eq->m_rrlast=0;assert(eq->GetNextQindex(paused)==1);
 std::cout<<"PASS: congestion-rate service weights, changing grants, blocked-credit bound, short-message priority and eligibility\n";
}
