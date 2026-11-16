#include "ns3/rdma-hw.h"
#include <cassert>
#include <cmath>
#include <iostream>
#include <limits>
using namespace ns3;
int main() {
 // Regression from observed flow 4688: arrivals still look like 100 Gb/s,
 // but the most recently issued grant is only 100 Mb/s. Releasing 763 KB
 // would leave tens of milliseconds of work outside receiver allocation.
 auto threshold=RdmaHw::ComputeGuardGrantBoundedReleaseBytes(12.5e9,100000000,8.32e-6,8);
 assert(threshold<=832 && threshold>=831);assert(763317>=threshold);
 for(double gamma : {0.,1.,2.,8.}) for(double rtt : {0.,4.16e-6,8.32e-6,1e-3}) {
  uint64_t previous=0;
  for(uint64_t rate : {0ULL,1000000ULL,100000000ULL,1000000000ULL,100000000000ULL}) {
   auto n=RdmaHw::ComputeGuardGrantBoundedReleaseBytes(12.5e9,rate,rtt,gamma);
   assert(n>=previous);previous=n;
   assert((long double)n<=rate/8.0L*rtt*gamma+1e-6L);
   assert((long double)n<=12.5e9L*rtt*gamma+1e-6L);
  }
 }
 // Low measured delivery continues to constrain release even with a large
 // grant. High grants preserve early release when enough service exists.
 assert(RdmaHw::ComputeGuardGrantBoundedReleaseBytes(1e6,100000000000ULL,1e-3,1)==1000);
 assert(RdmaHw::ComputeGuardGrantBoundedReleaseBytes(12.5e9,100000000000ULL,8e-6,8)>=799999);
 assert(RdmaHw::ComputeGuardGrantBoundedReleaseBytes(-1,100000000,8e-6,8)==0);
 assert(RdmaHw::ComputeGuardGrantBoundedReleaseBytes(std::numeric_limits<double>::infinity(),100000000,8e-6,8)==0);
 assert(RdmaHw::ComputeGuardGrantBoundedReleaseBytes(std::numeric_limits<double>::quiet_NaN(),100000000,8e-6,8)==0);
 std::cout<<"PASS: stale-arrival burst after grant reduction, retained service bound, measured-rate bound, zero/invalid inputs\n";
}
