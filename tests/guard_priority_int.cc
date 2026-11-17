#include "ns3/broadcom-egress-queue.h"
#include "ns3/packet.h"
#include <cassert>
#include <iostream>
using namespace ns3;
int main() {
 auto q=CreateObject<BEgressQueue>();q->SetStrictPriority(true);
 uint32_t sum=0;
 for(uint32_t i=0;i<8;++i) {
  assert(q->Enqueue(Create<Packet>((i+1)*100),i));sum+=(i+1)*100;
  assert(q->GetNBytesThroughPriority(i)==sum);
 }
 assert(q->GetNBytesThroughPriority(0)==100);
 assert(q->GetNBytesThroughPriority(7)==q->GetNBytesTotal());
 assert(q->GetNBytesThroughPriority(3)==1000);
 assert(q->Enqueue(Create<Packet>(100000),7));
 assert(q->GetNBytesThroughPriority(3)==1000); // lower queue cannot delay higher-priority service
 bool paused[8]={false};auto p=q->DequeueRR(paused);assert(p->GetSize()==100);
 assert(q->GetNBytesThroughPriority(3)==900);
 p=q->DequeueRR(paused);assert(p->GetSize()==200);
 assert(q->GetNBytesThroughPriority(3)==700);
 assert(q->GetNBytesThroughPriority(7)==q->GetNBytesTotal());
 std::cout<<"PASS: queue-prefix feedback includes higher/equal queues, excludes lower queues, tracks dequeue, and lowest class sees all bytes\n";
}
