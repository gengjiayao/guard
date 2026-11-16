#include "ns3/rdma-hw.h"
#include "ns3/rdma-queue-pair.h"
#include <cassert>
#include <iostream>
using namespace ns3;
int main() {
 auto hw=CreateObject<RdmaHw>();hw->m_cc_mode=11;hw->m_guardPostGrantWindowBdps=2;
 hw->m_guardFixedWindow=true;hw->m_guardSelectiveRegistration=true;
 auto qp=CreateObject<RdmaQueuePair>(3,Ipv4Address(1),Ipv4Address(2),1,2);
 qp->m_win=104000;qp->m_size=1000000;qp->m_var_win=false;
 qp->m_rate=DataRate(1000000000ULL);qp->hp.m_grantRate=DataRate(0);
 qp->snd_nxt=104000;qp->snd_una=0;
 assert(qp->IsWinBound() && qp->GetWin()==104000);
 assert(!hw->MaybeExpandGuardPostGrantWindow(qp)); // no grant: original flight bound
 qp->hp.m_grantRate=DataRate(50000000000ULL);
 assert(hw->MaybeExpandGuardPostGrantWindow(qp));
 assert(qp->GetWin()==208000 && !qp->IsWinBound());
 assert(qp->GetGuardFirstGrantWin()==104000);
 assert(qp->m_rate.GetBitRate()==1000000000ULL && qp->hp.m_grantRate.GetBitRate()==50000000000ULL);
 assert(!hw->MaybeExpandGuardPostGrantWindow(qp) && hw->m_guardPostGrantWindowRaises==1);
 qp->m_guard_wait_first_grant=true;assert(qp->IsWinBound());qp->m_guard_wait_first_grant=false;
 qp->snd_nxt=208000;assert(qp->IsWinBound());
 qp->m_guard_transport_win=0;qp->m_size=150000;hw->m_guardPostGrantWindowBdps=4;
 assert(hw->MaybeExpandGuardPostGrantWindow(qp));assert(qp->GetWin()==150000);
 qp->m_guard_transport_win=0;hw->m_guardRegistrationThresholdBdps=4;
 assert(!hw->MaybeExpandGuardPostGrantWindow(qp)); // passive message has no receiver authority
 hw->m_guardRegistrationThresholdBdps=1;hw->m_guardPostGrantWindowBdps=1;
 assert(!hw->MaybeExpandGuardPostGrantWindow(qp));
 std::cout<<"PASS: initial flight unchanged, valid-grant gate, bounded window, unchanged rate caps, idempotence, passive exclusion\n";
}
