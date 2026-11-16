#include "ns3/rdma-hw.h"
#include "ns3/rdma-queue-pair.h"
#include <cassert>
#include <iostream>
using namespace ns3;
int main() {
 auto hw=CreateObject<RdmaHw>();hw->m_cc_mode=11;hw->m_guardSelectiveRegistration=true;
 for(uint64_t bdp:{1000ULL,52000ULL,104000ULL}) {
  hw->m_guardRegistrationThresholdBdps=1;
  for(uint64_t size:std::vector<uint64_t>{1ULL,bdp,bdp+1,4*bdp,16*bdp}) {
   assert(hw->GuardNeedsReceiverControl(size,bdp)==(size>bdp));
   assert(!hw->UsesGuardPassiveControl(size,bdp));
  }
  for(unsigned threshold:{2,4,8,16}) {
   hw->m_guardRegistrationThresholdBdps=threshold;
   assert(!hw->GuardNeedsReceiverControl(threshold*bdp,bdp));
   assert(hw->GuardNeedsReceiverControl(threshold*bdp+1,bdp));
   for(uint64_t size=1;size<20*bdp;size+=std::max<uint64_t>(1,bdp/17)) {
    unsigned classes=(size<=bdp)+hw->UsesGuardPassiveControl(size,bdp)+hw->GuardNeedsReceiverControl(size,bdp);
    assert(classes==1);
   }
  }
 }
 hw->m_guardRegistrationThresholdBdps=8;
 auto qp=CreateObject<RdmaQueuePair>(3,Ipv4Address(1),Ipv4Address(2),1,2);
 qp->m_baseRtt=8000;qp->m_max_rate=DataRate(100000000000ULL);
 qp->m_size=400000;qp->m_guard_tail_bypass=true;
 assert(hw->UsesGuardPassiveControl(qp->m_size,100000));
 assert(!hw->UsesGuardTailBypass(qp)); // passive feedback must remain binding
 qp->m_size=2000000;assert(!hw->UsesGuardPassiveControl(qp->m_size,100000));
 assert(hw->UsesGuardTailBypass(qp));
 hw->m_guardSelectiveRegistration=false;
 assert(hw->GuardNeedsReceiverControl(1000,100000));
 assert(!hw->UsesGuardPassiveControl(400000,100000));
 std::cout<<"PASS: default admission, disjoint bounded-message classes, exact threshold boundaries, no tail bypass without receiver authority\n";
}
