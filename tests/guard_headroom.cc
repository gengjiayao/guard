#include "ns3/rdma-hw.h"
#include <cassert>
#include <iostream>
#include <random>
#include <vector>
using namespace ns3;
int main() {
 const uint64_t C=100000000000ULL;
 for(uint64_t r:{0ULL,1ULL,1000000ULL,50000000000ULL,100000000000ULL}) {
  assert(RdmaHw::ComputeGuardHeadroomGrant(r,C,1)==r);
  assert(RdmaHw::ComputeGuardHeadroomGrant(r,C,2)<=C);
 }
 assert(RdmaHw::ComputeGuardHeadroomGrant(C/4,C,2)==C/2);
 assert(RdmaHw::ComputeGuardHeadroomGrant(C,C,2)==C);
 std::mt19937 rng(71);
 for(unsigned n=1;n<100;++n)for(double factor:{1.,1.25,1.5,2.}) {
  uint64_t remaining=C,total=0;
  for(unsigned i=0;i<n;++i) {
   uint64_t r=i+1==n?remaining:((uint64_t)rng()*rng())%(remaining+1);
   remaining-=r;auto grant=RdmaHw::ComputeGuardHeadroomGrant(r,C,factor);
   assert(grant<=C && grant>=r);total+=grant;
  }
  assert(total<=factor*C);
 }
 std::cout<<"PASS: unchanged default, per-NIC physical cap, bounded aggregate permissions, rounding bounds\n";
}
