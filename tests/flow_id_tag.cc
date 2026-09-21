#include "ns3/packet.h"
#include "ns3/flow-id-num-tag.h"
#include <iostream>
#include <stdint.h>
using namespace ns3;
int main() {
  const int32_t ids[] = {0, 1, 65535, 65536, 65552, 131088, 2147483647};
  bool ok = true;
  for (auto id : ids) {
    Ptr<Packet> p = Create<Packet>(64);
    FlowIDNUMTag input; input.SetId(id); input.SetFlowSize(951625);
    p->AddPacketTag(input);
    Ptr<Packet> copy = p->Copy();
    FlowIDNUMTag output;
    if (!copy->PeekPacketTag(output) || output.GetId()!=id ||
        output.GetFlowSize()!=951625 || copy->GetSize()!=64 || input.GetSerializedSize()!=8) {
      std::cout << "FAIL id=" << id << " recovered=" << output.GetId() << "\n"; ok=false;
    }
  }
  if(ok) std::cout << "PASS full-width flow IDs and sizes survive actual Packet tag round trips and copies without changing wire size\n";
  return ok?0:1;
}
