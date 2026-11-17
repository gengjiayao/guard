#include "ns3/rdma-hw.h"
#include <cassert>
#include <algorithm>
#include <iostream>
#include <deque>
using namespace ns3;
int main(){
 const uint64_t mtu=1000,size=2000123;
 uint64_t compact=0,acks=0;
 // Different batching and return delays, including periodic lost ACKs:
 // receiver ACK clock is unchanged and every generated cumulative ACK has INT.
 for(unsigned stride:{1,2,4,8,16,32,64})for(unsigned batch:{1,2,4,8,16,32,64})for(unsigned delay:{0,1,3,16,65}){
  uint64_t una=0,receiver_ack=0;std::deque<std::pair<uint64_t,uint64_t>> pending;
  unsigned ordinal=0;uint64_t last_sample=0;
  for(uint64_t seq=0;seq<size;seq+=mtu,++ordinal){
   while(!pending.empty()&&pending.front().first<=ordinal){una=std::max(una,pending.front().second);pending.pop_front();}
   uint64_t payload=std::min(mtu,size-seq),end=seq+payload;
   bool drain=(ordinal%233)==97;
   bool full=RdmaHw::ShouldGuardCarryInt(seq,payload,size,una,mtu,batch,stride,drain);
   bool ack=receiver_ack==0 || end>=receiver_ack+batch*mtu || end==size || drain;
   if(ack){assert(full);++acks;receiver_ack=end;if(ordinal%19!=7)pending.push_back({ordinal+delay,end});}
   if(full)last_sample=ordinal;else{++compact;assert(stride>1);assert(ordinal-last_sample<stride);}
   if(stride==1)assert(full);
  }
 }
 assert(compact>0 && acks>0);
 assert(RdmaHw::ShouldGuardCarryInt(1501,1000,size,1000,mtu,16,8,false));
 assert(RdmaHw::ShouldGuardCarryInt(15000,1000,size,1000,mtu,16,8,true));
 std::cout<<"PASS: unchanged cumulative ACK clock, all ACK/drain/first/final packets carry telemetry, bounded sampling gap, delayed/lost ACK conservatism, default compatibility; compact="<<compact<<" ACKs="<<acks<<"\n";
}
