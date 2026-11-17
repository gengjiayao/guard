#include "ns3/qbb-net-device.h"
#include "ns3/rdma-queue-pair.h"
#include "ns3/int-header.h"
#include "ns3/settings.h"
#include <cassert>
#include <iostream>
using namespace ns3;
static Ptr<Packet> send(Ptr<RdmaQueuePair> q) {
 uint64_t n=std::min<uint64_t>(1000,q->GetBytesLeft());q->snd_nxt+=n;q->snd_una=q->snd_nxt;return Create<Packet>(n);
}
static Ptr<RdmaQueuePair> make(unsigned pg) {
 auto q=CreateObject<RdmaQueuePair>(pg,Ipv4Address(1),Ipv4Address(2),100+pg,200);
 q->SetSize(100000000);q->SetWin(100000);q->SetVarWin(false);q->SetBaseRtt(8000);
 q->m_max_rate=q->m_rate=DataRate(100000000000ULL);q->m_guard_sender_srpt=true;
 q->m_guard_srpt_quantum_packets=4;q->m_flow_id=pg*10;return q;
}
int main() {
 IntHeader::mode=0;Settings::guard_sender_service_budget=true;
 auto eq=CreateObject<RdmaEgressQueue>();eq->m_qpGrp=CreateObject<RdmaQueuePairGroup>();eq->m_rdmaGetNxtPkt=MakeCallback(&send);
 auto a=make(1),b=make(2),c=make(3);eq->m_qpGrp->AddQp(a);eq->m_qpGrp->AddQp(b);eq->m_qpGrp->AddQp(c);
 bool paused[8]={false};unsigned count[3]={0};
 for(unsigned i=0;i<300;++i) {
  a->m_size=a->snd_nxt+(i%2?3000:2000);b->m_size=b->snd_nxt+(i%2?2000:3000);
  uint32_t before=eq->m_guardServiceSinceFair;
  int j=eq->GetNextQindex(paused);for(int k=0;k<5;++k)assert(eq->GetNextQindex(paused)==j);
  assert(eq->m_guardServiceSinceFair==before && j>=0);++count[j];eq->DequeueQindex(j);
 }
 assert(count[2]>=19 && count[2]<=21); // changing shortest identities cannot starve the long QP
 paused[3]=true;
 for(int i=0;i<40;++i) {a->m_size=a->snd_nxt+2000;b->m_size=b->snd_nxt+3000;int j=eq->GetNextQindex(paused);assert(j!=2);eq->DequeueQindex(j);}
 paused[3]=false;unsigned served=0;
 for(int i=0;i<20;++i) {a->m_size=a->snd_nxt+2000;b->m_size=b->snd_nxt+3000;int j=eq->GetNextQindex(paused);served+=j==2;eq->DequeueQindex(j);}assert(served>=1);
 uint32_t before=eq->m_guardServiceSinceFair;eq->m_ackQ->Enqueue(Create<Packet>(60));
 assert(eq->GetNextQindex(paused)==-1);eq->DequeueQindex(-1);assert(eq->m_guardServiceSinceFair==before);
 assert(a->m_rate.GetBitRate()==100000000000ULL && b->m_rate==a->m_rate && c->m_rate==a->m_rate);
 Settings::guard_sender_service_budget=false;
 std::cout<<"PASS: long-flow service despite changing shortest identity, dequeue-only accounting, stable fair rotation, PFC exclusion, control exclusion, unchanged rate caps\n";
}
