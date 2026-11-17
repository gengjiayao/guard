#include "ns3/rdma-hw.h"
#include "ns3/rdma-queue-pair.h"
#include <cassert>
#include <algorithm>
#include <iostream>
#include <random>
#include <map>
using namespace ns3;
int main() {
 auto hw=CreateObject<RdmaHw>();const uint64_t C=100000000000ULL;
 hw->m_guardSenderFairShare=true;hw->m_guardSenderFairExponent=0;hw->m_guardMinShareFraction=0;
 std::vector<Ptr<RdmaRxQueuePair>> fs;
 uint32_t peers[]={10,10,20,30,30,30};uint64_t bytes[]={1000000,16000000,2000000,3000000,6000000,30000000};
 for(unsigned i=0;i<6;++i){auto f=CreateObject<RdmaRxQueuePair>();f->dip=peers[i];f->m_flow_id=i;f->m_guard_flow_size=bytes[i];fs.push_back(f);hw->m_rate_flow_ctl_set.insert(PeekPointer(f));}
 auto classic=hw->ComputeGuardSenderFairTargets(C);
 hw->m_guardSenderFairParallel=true;hw->m_guardSenderFairWithinExponent=1;
 auto fair=hw->ComputeGuardSenderFairTargets(C);
 assert(fair[PeekPointer(fs[1])]>classic[PeekPointer(fs[1])]*50);
 assert(fair[PeekPointer(fs[0])]<=4*fair[PeekPointer(fs[1])]);
 auto budgets=[](const std::unordered_map<RdmaRxQueuePair*,uint64_t> &v){std::map<uint32_t,uint64_t> b;for(auto &kv:v)b[kv.first->dip]+=kv.second;return b;};
 auto before=budgets(fair);for(auto &kv:before)assert(kv.second<=C/3 && C/3-kv.second<4);
 // More messages cannot increase their physical sender's total budget.
 auto extra=CreateObject<RdmaRxQueuePair>();extra->dip=10;extra->m_flow_id=9;extra->m_guard_flow_size=20000000;fs.push_back(extra);hw->m_rate_flow_ctl_set.insert(PeekPointer(extra));
 auto after=budgets(hw->ComputeGuardSenderFairTargets(C));
 assert(after[10]<=before[10]+3 && before[10]<=after[10]+3);
 assert(after[20]==before[20] && after[30]==before[30]);
 std::mt19937 rng(6613);
 for(unsigned iteration=0;iteration<300;++iteration) {
  for(auto f:fs){f->m_guard_flow_size=10000+rng()%50000000;f->ReceiverNextExpectedSeq=rng()%f->m_guard_flow_size;}
  hw->m_guardSenderFairWithinExponent=(iteration%201)/100.;
  hw->m_guardSenderFairExponent=iteration%2;auto a=hw->ComputeGuardSenderFairTargets(C);
  uint64_t sum=0;for(auto &kv:a){assert(kv.second>0);sum+=kv.second;}
  assert(sum<=C && C-sum<fs.size()+3);
  auto b=budgets(a);uint64_t lo=C,hi=0;for(auto &kv:b){lo=std::min(lo,kv.second);hi=std::max(hi,kv.second);}assert(hi<=4*lo+fs.size());
  std::shuffle(fs.begin(),fs.end(),rng);hw->m_rate_flow_ctl_set.clear();for(auto f:fs)hw->m_rate_flow_ctl_set.insert(PeekPointer(f));
  assert(a==hw->ComputeGuardSenderFairTargets(C));
 }
 std::cout<<"PASS: capacity conservation, bounded source preference, same-source long progress, no budget multiplication by message count, permutation invariance\n";
}
