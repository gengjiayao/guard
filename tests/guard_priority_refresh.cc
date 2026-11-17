#include "ns3/rdma-hw.h"
#include <cassert>
#include <iostream>
using namespace ns3;
int main() {
 const uint64_t bdp=100000;
 for(double growth:{2.,3.,4.,8.}) {
  uint16_t previous=1;
  for(uint64_t bytes=1;bytes<100000000;bytes+=113) {
   auto pg=RdmaHw::ComputeGuardSizePriority(bytes,bdp,true,growth);
   assert(pg>=previous && pg>=1 && pg<=7);previous=pg;
   if(bytes<bdp)assert(pg==1);
  }
 }
 assert(RdmaHw::ComputeGuardSizePriority(4000000,bdp,true)==7);
 assert(RdmaHw::ComputeGuardSizePriority(4000000,bdp,true,4)==4);
 assert(RdmaHw::ComputeGuardSizePriority(8000000,bdp,true,4)==5);
 assert(RdmaHw::ComputeGuardSizePriority(30000000,bdp,true,4)==6);
 assert(RdmaHw::ComputeGuardSizePriority(8000000,bdp,true,4,2)==5);
 assert(RdmaHw::ComputeGuardSizePriority(20000000,bdp,true,4,2)==6);
 assert(RdmaHw::ComputeGuardSizePriority(30000000,bdp,true,4,2)==7);
 auto duplicate=RdmaHw::IsGuardDuplicateRefresh;
 assert(duplicate(10,10,100,8000,"progress",0,false));
 assert(duplicate(10,10,31999,8000,"demand",0,false));
 assert(!duplicate(10,10,32000,8000,"progress",0,false));
 assert(!duplicate(0,10,100,8000,"progress",0,false));
 assert(!duplicate(10,11,100,8000,"progress",0,false));
 assert(!duplicate(10,9,100,8000,"progress",0,false));
 assert(!duplicate(10,10,100,8000,"progress",1,false));
 assert(!duplicate(10,10,100,8000,"progress",0,true));
 for(const char* reason:{"register","release","add","remove","membership_batch","reliability_refresh"})
  assert(!duplicate(10,10,100,8000,reason,0,false));
 std::cout<<"PASS: monotone immutable queue classes, one-BDP boundary, unchanged-rate filtering, refresh deadline and lifecycle exclusions\n";
}
