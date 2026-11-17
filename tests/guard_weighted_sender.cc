#include "ns3/rdma-hw.h"
#include "ns3/rdma-queue-pair.h"
#include <cassert>
#include <algorithm>
#include <iostream>
#include <random>
using namespace ns3;
int main() {
 auto hw=CreateObject<RdmaHw>();hw->m_guardSenderFairShare=true;hw->m_guardMinShareFraction=0;
 const uint64_t C=100000000000ULL;std::vector<Ptr<RdmaRxQueuePair>> fs;
 for(unsigned i=0;i<6;++i) {
  auto f=CreateObject<RdmaRxQueuePair>();f->dip=10+i/2;f->m_flow_id=i;
  f->m_guard_flow_size=(i<2?2000000:i<4?4000000:40000000)+(i%2)*1000000;
  fs.push_back(f);hw->m_rate_flow_ctl_set.insert(PeekPointer(f));
 }
 auto at=[&](const std::unordered_map<RdmaRxQueuePair*,uint64_t>&v,unsigned i){return v.at(PeekPointer(fs[i]));};
 hw->m_guardSenderFairExponent=0;auto equal=hw->ComputeGuardSenderFairTargets(C);
 assert(at(equal,0)==at(equal,2) && at(equal,2)==at(equal,4));
 hw->m_guardSenderFairExponent=1;auto weighted=hw->ComputeGuardSenderFairTargets(C);
 assert(at(weighted,0)>at(weighted,2) && at(weighted,2)>at(weighted,4));
 assert(at(weighted,0)<=4*at(weighted,4));
 for(unsigned i=1;i<6;i+=2)assert(at(weighted,i)==at(equal,i));
 hw->m_guardSenderFairExponent=1;
 fs[4]->ReceiverNextExpectedSeq=39000000;
 auto nearing=hw->ComputeGuardSenderFairTargets(C);assert(at(nearing,4)>at(nearing,0));
 std::mt19937 rng(9917);
 for(unsigned t=0;t<500;++t) {
  for(auto f:fs){f->m_guard_flow_size=10000+rng()%30000000;f->ReceiverNextExpectedSeq=rng()%f->m_guard_flow_size;}
  hw->m_guardSenderFairExponent=(t%201)/100.0;hw->m_guardSenderFairRatio=1+t%64;
  auto before=hw->ComputeGuardSenderFairTargets(C);uint64_t sum=0;
  for(auto &kv:before){sum+=kv.second;assert(kv.second>0);}
  assert(sum<=C && C-sum<fs.size());
  std::shuffle(fs.begin(),fs.end(),rng);hw->m_rate_flow_ctl_set.clear();
  for(auto f:fs)hw->m_rate_flow_ctl_set.insert(PeekPointer(f));
  assert(before==hw->ComputeGuardSenderFairTargets(C));
 }
 std::cout<<"PASS: equal-mode compatibility, remaining-work preference, bounded weight ratio, per-source deduplication, floors, capacity and permutation invariance\n";
}
