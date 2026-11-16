#include "ns3/rdma-hw.h"
#include "ns3/rdma-queue-pair.h"
#include "ns3/double.h"
#include <algorithm>
#include <cassert>
#include <iostream>
#include <random>
#include <vector>
using namespace ns3;
int main() {
 const uint64_t capacity=100000000000ULL;
 auto hw=CreateObject<RdmaHw>(); hw->m_cc_mode=11;
 hw->m_guardReceiverConcurrency=2; hw->m_guardDuplexAdaptive=false;
 hw->m_guardLongFlowThresholdBdps=16; hw->m_guardRemainingAware=true;
 hw->m_guardRemainingExponent=1; hw->m_guardMinShareFraction=0;
 std::vector<Ptr<RdmaRxQueuePair>> flows;
 for(unsigned i=0;i<8;++i) {
  auto f=CreateObject<RdmaRxQueuePair>(); f->sip=1;f->dip=i+2;f->m_flow_id=i;
  f->m_guard_flow_size=4000000+i*1000000;f->ReceiverNextExpectedSeq=0;
  f->m_base_rtt_sec=8e-6; flows.push_back(f);hw->m_rate_flow_ctl_set.insert(PeekPointer(f));
 }
 // Long flows all receive useful capacity, regardless of message length.
 auto equal=hw->ComputeGuardBaseTargets(capacity);
 for(auto &kv:equal)assert(kv.second==capacity/8);
 assert(hw->m_guardLongFairAllocations==1);
 // Received-byte progress moves a flow into bounded-work service. It must
 // be promoted without requiring knowledge of future arrivals or a CDF.
 flows[0]->ReceiverNextExpectedSeq=flows[0]->m_guard_flow_size-100000;
 flows[1]->ReceiverNextExpectedSeq=flows[1]->m_guard_flow_size-200000;
 auto short_first=hw->ComputeGuardBaseTargets(capacity);
 assert(short_first[PeekPointer(flows[0])]>capacity/2);
 assert(short_first[PeekPointer(flows[1])]>capacity/4);
 assert(short_first[PeekPointer(flows[2])]<capacity/100);
 // After the short work completes, the long-flow pool immediately regains
 // the entire capacity instead of waiting for a periodic fairness timer.
 hw->m_rate_flow_ctl_set.erase(PeekPointer(flows[0]));
 hw->m_rate_flow_ctl_set.erase(PeekPointer(flows[1]));
 auto resumed=hw->ComputeGuardBaseTargets(capacity);
 for(auto &kv:resumed)assert(kv.second==capacity/6);
 // Capacity, positivity and repeatability across mixed sizes, progress and
 // fractional minimum-rate floors. Test the live allocator, not a replica.
 std::mt19937 rng(177);
 for(unsigned trial=0;trial<500;++trial) {
  hw->m_rate_flow_ctl_set.clear();
  for(auto f:flows) {f->m_guard_flow_size=1000+rng()%30000000;f->ReceiverNextExpectedSeq=rng()%f->m_guard_flow_size;}
  hw->m_guardMinShareFraction=(trial%5)*.2;
  for(auto f:flows)hw->m_rate_flow_ctl_set.insert(PeekPointer(f));
  auto a=hw->ComputeGuardBaseTargets(capacity); uint64_t sum=0;
  for(auto &kv:a) {assert(kv.second>0 && kv.second<=capacity);sum+=kv.second;}
  assert(sum<=capacity && capacity-sum<flows.size());
  std::shuffle(flows.begin(),flows.end(),rng);hw->m_rate_flow_ctl_set.clear();
  for(auto f:flows)hw->m_rate_flow_ctl_set.insert(PeekPointer(f));
  auto b=hw->ComputeGuardBaseTargets(capacity);assert(a==b);
 }
 hw->m_guardLongFlowThresholdBdps=0;
 auto before=hw->m_guardLongFairAllocations;hw->ComputeGuardBaseTargets(capacity);
 assert(before==hw->m_guardLongFairAllocations);
 std::cout<<"PASS: long-flow service, progress promotion, capacity conservation, deterministic allocation, disabled mode\n";
}
