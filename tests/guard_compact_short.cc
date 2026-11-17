#include "ns3/seq-ts-header.h"
#include "ns3/custom-header.h"
#include "ns3/udp-header.h"
#include "ns3/ipv4-header.h"
#include "ns3/ppp-header.h"
#include "ns3/packet.h"
#include <cassert>
#include <vector>
#include <iostream>
using namespace ns3;
int main() {
 IntHeader::mode=0;
 for(bool compact:{false,true}) for(uint16_t pg=1;pg<=7;++pg) {
  std::vector<uint8_t> payload(1000);for(unsigned i=0;i<payload.size();++i)payload[i]=(i*17+3)%256;
  auto p=Create<Packet>(payload.data(),payload.size());
  SeqTsHeader seq;seq.SetSeq(123000);seq.SetPG(pg);seq.SetGuardNoInt(compact);
  p->AddHeader(seq);assert(p->GetSize()==1000+6+(compact?0:42));
  auto copy=p->Copy();SeqTsHeader parsed;copy->RemoveHeader(parsed);
  assert(parsed.GetSeq()==123000 && parsed.GetPG()==pg && parsed.GetGuardNoInt()==compact);
  std::vector<uint8_t> actual(1000);copy->CopyData(actual.data(),actual.size());assert(actual==payload);
  UdpHeader udp;udp.SetSourcePort(17);udp.SetDestinationPort(29);p->AddHeader(udp);
  Ipv4Header ip;ip.SetProtocol(0x11);ip.SetSource(Ipv4Address(1));ip.SetDestination(Ipv4Address(2));
  ip.SetPayloadSize(p->GetSize());ip.SetTtl(64);p->AddHeader(ip);
  PppHeader ppp;ppp.SetProtocol(0x0021);p->AddHeader(ppp);
  CustomHeader ch(CustomHeader::L2_Header|CustomHeader::L3_Header|CustomHeader::L4_Header);
  p->PeekHeader(ch);assert(ch.udp.pg==pg && ch.udp.seq==123000 && ch.udp.guard_no_int==compact);
  assert(p->GetSize()-ch.GetSerializedSize()==1000);
  auto c=p->Copy();c->RemoveHeader(ch);assert(c->GetSize()==1000);
  c->CopyData(actual.data(),actual.size());assert(actual==payload);
  c->AddHeader(ch);CustomHeader again(CustomHeader::L2_Header|CustomHeader::L3_Header|CustomHeader::L4_Header);
  c->PeekHeader(again);assert(again.udp.pg==pg && again.udp.guard_no_int==compact);
  assert(c->GetSize()==p->GetSize());
 }
 IntHeader::mode=3;SeqTsHeader legacy;legacy.SetPG(7);assert(legacy.GetSerializedSize()==6 && !legacy.GetGuardNoInt());
 std::cout<<"PASS: compact/full DATA round trips, payload integrity, immutable PG identity, CustomHeader reserialization, exact 42-byte wire saving, Homa header unchanged\n";
}
