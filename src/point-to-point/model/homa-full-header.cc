#include "ns3/log.h"
#include "ns3/header.h"
#include "homa-full-header.h"

NS_LOG_COMPONENT_DEFINE ("HomaFullHeader");

namespace ns3 {

NS_OBJECT_ENSURE_REGISTERED (HomaFullHeader);

HomaFullHeader::HomaFullHeader()
    : m_type(DATA),
      m_message_id(0),
      m_msg_total_length(0),
      m_pkt_offset(0),
      m_pkt_length(0),
      m_unscheduled_bytes(0),
      m_priority(0),
      m_granted_offset(0),
      m_grant_priority(0),
      m_resend_offset(0),
      m_resend_length(0),
      m_restart_priority(0) {}

void HomaFullHeader::SetType(uint8_t t) { m_type = t; }
uint8_t HomaFullHeader::GetType() const { return m_type; }
void HomaFullHeader::SetMessageId(uint64_t id) { m_message_id = id; }
uint64_t HomaFullHeader::GetMessageId() const { return m_message_id; }

void HomaFullHeader::SetMsgTotalLength(uint64_t len) { m_msg_total_length = len; }
uint64_t HomaFullHeader::GetMsgTotalLength() const { return m_msg_total_length; }
void HomaFullHeader::SetPktOffset(uint64_t off) { m_pkt_offset = off; }
uint64_t HomaFullHeader::GetPktOffset() const { return m_pkt_offset; }
void HomaFullHeader::SetPktLength(uint32_t len) { m_pkt_length = len; }
uint32_t HomaFullHeader::GetPktLength() const { return m_pkt_length; }
void HomaFullHeader::SetUnscheduledBytes(uint64_t b) { m_unscheduled_bytes = b; }
uint64_t HomaFullHeader::GetUnscheduledBytes() const { return m_unscheduled_bytes; }
void HomaFullHeader::SetPriority(uint8_t p) { m_priority = p; }
uint8_t HomaFullHeader::GetPriority() const { return m_priority; }

void HomaFullHeader::SetGrantedOffset(uint64_t off) { m_granted_offset = off; }
uint64_t HomaFullHeader::GetGrantedOffset() const { return m_granted_offset; }
void HomaFullHeader::SetGrantPriority(uint8_t p) { m_grant_priority = p; }
uint8_t HomaFullHeader::GetGrantPriority() const { return m_grant_priority; }

void HomaFullHeader::SetResendOffset(uint64_t off) { m_resend_offset = off; }
uint64_t HomaFullHeader::GetResendOffset() const { return m_resend_offset; }
void HomaFullHeader::SetResendLength(uint64_t len) { m_resend_length = len; }
uint64_t HomaFullHeader::GetResendLength() const { return m_resend_length; }
void HomaFullHeader::SetRestartPriority(uint8_t p) { m_restart_priority = p; }
uint8_t HomaFullHeader::GetRestartPriority() const { return m_restart_priority; }

TypeId HomaFullHeader::GetTypeId(void) {
    static TypeId tid = TypeId("ns3::HomaFullHeader")
                            .SetParent<Header>()
                            .AddConstructor<HomaFullHeader>();
    return tid;
}

TypeId HomaFullHeader::GetInstanceTypeId(void) const { return GetTypeId(); }

void HomaFullHeader::Print(std::ostream &os) const {
    os << "HomaFullHeader: type=" << (uint32_t)m_type
       << " mid=" << m_message_id
       << " total=" << m_msg_total_length
       << " off=" << m_pkt_offset
       << " len=" << m_pkt_length
       << " prio=" << (uint32_t)m_priority
       << " grantOff=" << m_granted_offset
       << " grantPrio=" << (uint32_t)m_grant_priority
       << " resendOff=" << m_resend_offset
       << " resendLen=" << m_resend_length;
}

uint32_t HomaFullHeader::GetSerializedSize(void) const { return GetHeaderSize(); }

uint32_t HomaFullHeader::GetHeaderSize(void) {
    // 1+8+8+8+4+8+1+8+1+8+8+1 = 64 bytes
    return 1 + sizeof(uint64_t)        // type, message_id
         + sizeof(uint64_t)            // msg_total_length
         + sizeof(uint64_t)            // pkt_offset
         + sizeof(uint32_t)            // pkt_length
         + sizeof(uint64_t)            // unscheduled_bytes
         + 1                           // priority
         + sizeof(uint64_t)            // granted_offset
         + 1                           // grant_priority
         + sizeof(uint64_t)            // resend_offset
         + sizeof(uint64_t)            // resend_length
         + 1;                          // restart_priority
}

void HomaFullHeader::Serialize(Buffer::Iterator start) const {
    Buffer::Iterator i = start;
    i.WriteU8(m_type);
    i.WriteHtonU64(m_message_id);
    i.WriteHtonU64(m_msg_total_length);
    i.WriteHtonU64(m_pkt_offset);
    i.WriteHtonU32(m_pkt_length);
    i.WriteHtonU64(m_unscheduled_bytes);
    i.WriteU8(m_priority);
    i.WriteHtonU64(m_granted_offset);
    i.WriteU8(m_grant_priority);
    i.WriteHtonU64(m_resend_offset);
    i.WriteHtonU64(m_resend_length);
    i.WriteU8(m_restart_priority);
}

uint32_t HomaFullHeader::Deserialize(Buffer::Iterator start) {
    Buffer::Iterator i = start;
    m_type = i.ReadU8();
    m_message_id = i.ReadNtohU64();
    m_msg_total_length = i.ReadNtohU64();
    m_pkt_offset = i.ReadNtohU64();
    m_pkt_length = i.ReadNtohU32();
    m_unscheduled_bytes = i.ReadNtohU64();
    m_priority = i.ReadU8();
    m_granted_offset = i.ReadNtohU64();
    m_grant_priority = i.ReadU8();
    m_resend_offset = i.ReadNtohU64();
    m_resend_length = i.ReadNtohU64();
    m_restart_priority = i.ReadU8();
    return GetSerializedSize();
}

} // namespace ns3
