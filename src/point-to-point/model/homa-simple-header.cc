#include "ns3/log.h"
#include "ns3/header.h"
#include "homa-simple-header.h"

NS_LOG_COMPONENT_DEFINE ("HomaSimpleHeader");

namespace ns3 {

NS_OBJECT_ENSURE_REGISTERED (HomaSimpleHeader);

HomaSimpleHeader::HomaSimpleHeader(): m_bdp(0), m_homa_requset(0), m_homa_unscheduled(0) {}

void HomaSimpleHeader::SetBdp(uint64_t bdp) {
    m_bdp = bdp;
}

uint64_t HomaSimpleHeader::GetBdp(void) const {
    return m_bdp;
}

void HomaSimpleHeader::SetHomaRequest(uint64_t req) {
    m_homa_requset = req;
}

uint64_t HomaSimpleHeader::GetHomaRequest(void) const {
    return m_homa_requset;
}

void HomaSimpleHeader::SetHomaUnscheduled(uint64_t us) {
    m_homa_unscheduled = us;
}

uint64_t HomaSimpleHeader::GetHomaUnscheduled(void) const {
    return m_homa_unscheduled;
}

TypeId HomaSimpleHeader::GetTypeId(void) {
  static TypeId tid = TypeId("ns3::HomaSimpleHeader").SetParent<Header>().AddConstructor<HomaSimpleHeader>();
  return tid;
}

TypeId HomaSimpleHeader::GetInstanceTypeId(void) const {
    return GetTypeId();
}

void HomaSimpleHeader::Print(std::ostream &os) const {
    os << "HomaSimpleHeader: bdp=" << m_bdp
       << " homa_request=" << m_homa_requset
       << " homa_unscheduled=" << m_homa_unscheduled;
}

uint32_t HomaSimpleHeader::GetSerializedSize(void) const {
    return GetHeaderSize();
}

uint32_t HomaSimpleHeader::GetHeaderSize(void) {
    return sizeof(m_bdp) + sizeof(m_homa_requset) + sizeof(m_homa_unscheduled);
}

void HomaSimpleHeader::Serialize(Buffer::Iterator start) const {
    Buffer::Iterator i = start;
    i.WriteHtonU64(m_bdp);
    i.WriteHtonU64(m_homa_requset);
    i.WriteHtonU64(m_homa_unscheduled);
}

uint32_t HomaSimpleHeader::Deserialize(Buffer::Iterator start) {
    Buffer::Iterator i = start;
    m_bdp = i.ReadNtohU64();
    m_homa_requset = i.ReadNtohU64();
    m_homa_unscheduled = i.ReadNtohU64();
    return GetSerializedSize();
}

} // namespace ns3
