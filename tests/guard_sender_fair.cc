#include "ns3/rdma-hw.h"
#include "ns3/rdma-queue-pair.h"
#include <cassert>
#include <algorithm>
#include <iostream>
#include <random>
#include <vector>
using namespace ns3;
int main() {
 const uint64_t C=100000000000ULL;
 auto hw=CreateObject<RdmaHw>();hw->m_cc_mode=11;hw->m_guardReceiverConcurrency=2;
 hw->m_guardDuplexAdaptive=false;hw->m_guardRemainingAware=true;hw->m_guardRemainingExponent=1;
 std::vector<Ptr<RdmaRxQueuePair>> fs;
 for(unsigned i=0;i<6;++i) {
  auto f=CreateObject<RdmaRxQueuePair>();f->sip=1;f->dip=2+i/2;f->m_flow_id=i;
  f->m_guard_flow_size=4000000+i*1000000;f->ReceiverNextExpectedSeq=0;f->m_base_rtt_sec=8e-6;
  fs.push_back(f);hw->m_rate_flow_ctl_set.insert(PeekPointer(f));
 }
 hw->m_guardSenderFairShare=true;
 auto fair=hw->ComputeGuardBaseTargets(C);
 for(unsigned i=0;i<6;++i)assert(i%2 ? fair[PeekPointer(fs[i])]<C/100 : fair[PeekPointer(fs[i])]>C/4);
 // Remaining-byte progress, not original size, determines service within
 // a sender. The other sender budgets must remain unaffected.
 fs[1]->ReceiverNextExpectedSeq=4900000;
 auto switched=hw->ComputeGuardBaseTargets(C);
 assert(switched[PeekPointer(fs[1])]>C/4 && switched[PeekPointer(fs[0])]<C/100);
 assert(switched[PeekPointer(fs[2])]==fair[PeekPointer(fs[2])]);
 assert(switched[PeekPointer(fs[4])]==fair[PeekPointer(fs[4])]);
 // One large outlier does not trigger the fairness transition.
 assert(RdmaHw::ComputeGuardFairMixFraction({2,3,10000},16)==0);
 assert(RdmaHw::ComputeGuardFairMixFraction({32,64,96},16)==1);
 assert(RdmaHw::ComputeGuardFairMixFraction({16,24,32},16)==.5);
 assert(RdmaHw::ComputeGuardFairMixFraction({16,24,32},0)==0);
 assert(RdmaHw::ComputeGuardFairMixFraction({},16)==0);
 std::mt19937 rng(191);
 hw->m_guardSenderFairShare=false;
 for(unsigned trial=0;trial<500;++trial) {
  for(auto f:fs){f->m_guard_flow_size=10000+rng()%30000000;f->ReceiverNextExpectedSeq=rng()%f->m_guard_flow_size;}
  hw->m_guardFairMixThresholdBdps=0;auto base=hw->ComputeGuardBaseTargets(C);
  auto group=hw->ComputeGuardSenderFairTargets(C);
  hw->m_guardFairMixThresholdBdps=1+trial%64;auto mixed=hw->ComputeGuardBaseTargets(C);
  uint64_t sum=0;
  for(auto &kv:mixed){sum+=kv.second;assert(kv.second>0);assert(kv.second>=std::min(base[kv.first],group[kv.first]));assert(kv.second<=std::max(base[kv.first],group[kv.first]));}
  assert(sum<=C && C-sum<2*fs.size());
  std::shuffle(fs.begin(),fs.end(),rng);hw->m_rate_flow_ctl_set.clear();
  for(auto f:fs)hw->m_rate_flow_ctl_set.insert(PeekPointer(f));
  assert(mixed==hw->ComputeGuardBaseTargets(C));
 }
 std::cout<<"PASS: sender deduplication, progress-based service, unaffected peer budgets, adaptive endpoints, capacity and order invariants\n";
}
