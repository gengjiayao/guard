#include "ns3/rdma-hw.h"
#include "ns3/rdma-queue-pair.h"
#include <cassert>
#include <algorithm>
#include <iostream>
#include <deque>
using namespace ns3;
int main(){
 assert(CreateObject<RdmaQueuePair>(1,Ipv4Address(1),Ipv4Address(2),1,2)->m_guard_int_ack_anchor==0);
 const uint64_t mtu=1000,size=2000123;uint64_t compact=0,acks=0,conservative_full=0,predicted_full=0;
 for(unsigned stride:{2,4,8,16,32,64})for(unsigned batch:{1,2,4,8,16,32,64})for(unsigned delay:{0,1,3,16,65}){
  uint64_t anchor=0,receiver_ack=0;std::deque<std::pair<uint64_t,uint64_t>> pending;unsigned ordinal=0;uint64_t last_sample=0;
  for(uint64_t seq=0;seq<size;seq+=mtu,++ordinal){
   while(!pending.empty()&&pending.front().first<=ordinal){anchor=std::max(anchor,pending.front().second);pending.pop_front();}
   uint64_t payload=std::min(mtu,size-seq),end=seq+payload;bool drain=(ordinal%233)==97;
   bool full=RdmaHw::ShouldGuardCarryInt(seq,payload,size,anchor,mtu,batch,stride,drain,true);
   bool old=RdmaHw::ShouldGuardCarryInt(seq,payload,size,anchor,mtu,batch,stride,drain,false);
   assert(!full || old);predicted_full+=full;conservative_full+=old;
   bool ack=receiver_ack==0 || end>=receiver_ack+batch*mtu || end==size || drain;
   if(ack){assert(full);++acks;receiver_ack=end;
    if(drain){ // Actual sender cannot pass a promotion barrier until its ACK returns.
      anchor=end;pending.clear();
    }else if(ordinal%19!=7)pending.push_back({ordinal+delay,end});
   }
   if(full)last_sample=ordinal;else{++compact;assert(ordinal-last_sample<stride);}
  }
 }
 assert(compact>0 && acks>0 && predicted_full<conservative_full);
 // Replaying data before an observed ACK anchor retains telemetry.
 assert(RdmaHw::ShouldGuardCarryInt(5000,1000,size,17000,mtu,16,64,false,true));
 std::cout<<"PASS: fixed ACK grid including delayed/lost ACKs and drain-reset phases, exact ACK sample preservation, retransmission coverage; compact="<<compact<<" ACKs="<<acks<<" full="<<predicted_full<<" conservative="<<conservative_full<<"\n";
}
