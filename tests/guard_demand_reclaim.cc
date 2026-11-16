#include "ns3/rdma-hw.h"
#include "ns3/rdma-queue-pair.h"
#include <cassert>
#include <iostream>
#include <random>
#include <algorithm>
using namespace ns3;
int main() {
 const uint64_t C=100000000000ULL;
 auto hw=CreateObject<RdmaHw>();hw->m_cc_mode=11;hw->m_guardReceiverConcurrency=2;
 hw->m_guardDuplexAdaptive=false;hw->m_guardRemainingAware=true;hw->m_guardRemainingExponent=1;
 hw->m_guardMinShareFraction=0;hw->m_guardDemandThreshold=.75;
 std::vector<Ptr<RdmaRxQueuePair>> fs;
 for(unsigned i=0;i<4;++i) {
  auto f=CreateObject<RdmaRxQueuePair>();f->sip=1;f->dip=2+i;f->m_flow_id=i;
  f->m_guard_flow_size=200000*(i+1);f->ReceiverNextExpectedSeq=0;f->m_base_rtt_sec=8e-6;
  fs.push_back(f);hw->m_rate_flow_ctl_set.insert(PeekPointer(f));
 }
 auto base=hw->ComputeGuardBaseTargets(C);
 assert(hw->ComputeGuardDemandTargets(C)==base); // no evidence: no equal-share rewrite
 fs[0]->m_guard_demand_limited=true;fs[0]->m_guard_measured_rate_bps=1000000000ULL;
 auto moved=hw->ComputeGuardDemandTargets(C);
 assert(moved[PeekPointer(fs[0])]<2000000000ULL);
 assert(moved[PeekPointer(fs[1])]>base[PeekPointer(fs[1])]);
 assert(moved[PeekPointer(fs[2])]==base[PeekPointer(fs[2])]);
 uint64_t a=0,b=0;for(auto &x:base)a+=x.second;for(auto &x:moved)b+=x.second;assert(a==b && b<=C);
 fs[0]->m_guard_demand_limited=false;assert(hw->ComputeGuardDemandTargets(C)==base);
 for(auto f:fs)f->m_guard_demand_limited=true;
 assert(hw->ComputeGuardDemandTargets(C)==base); // no recipient: do not drain all grants
 std::mt19937 rng(135);
 for(unsigned t=0;t<500;++t) {
  for(auto f:fs){f->m_guard_flow_size=1000+rng()%10000000;f->ReceiverNextExpectedSeq=rng()%f->m_guard_flow_size;
   f->m_guard_demand_limited=rng()%2;f->m_guard_measured_rate_bps=rng()%1000000000;}
  auto raw=hw->ComputeGuardBaseTargets(C),q=hw->ComputeGuardDemandTargets(C);a=b=0;
  for(auto &x:raw)a+=x.second;for(auto &x:q){b+=x.second;assert(x.second>0 && x.second<=C);}
  assert(a==b && b<=C);
  std::shuffle(fs.begin(),fs.end(),rng);hw->m_rate_flow_ctl_set.clear();
  for(auto f:fs)hw->m_rate_flow_ctl_set.insert(PeekPointer(f));
  assert(q==hw->ComputeGuardDemandTargets(C));
 }
 std::cout<<"PASS: unchanged priority without idle-share evidence, bounded donor, shortest recipient, service restoration, no-recipient fallback, capacity and determinism\n";
}
