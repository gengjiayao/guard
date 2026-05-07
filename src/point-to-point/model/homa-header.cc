#include "ns3/log.h"
#include "ns3/header.h"
#include "homa-header.h"

NS_LOG_COMPONENT_DEFINE ("HomaHeader");

namespace ns3 {

NS_OBJECT_ENSURE_REGISTERED (HomaHeader);

HomaHeader::HomaHeader()
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

void HomaHeader::SetType(uint8_t t) { m_type = t; }
uint8_t HomaHeader::GetType() const { return m_type; }
void HomaHeader::SetMessageId(uint64_t id) { m_message_id = id; }
uint64_t HomaHeader::GetMessageId() const { return m_message_id; }

void HomaHeader::SetMsgTotalLength(uint64_t len) { m_msg_total_length = len; }
uint64_t HomaHeader::GetMsgTotalLength() const { return m_msg_total_length; }
void HomaHeader::SetPktOffset(uint64_t off) { m_pkt_offset = off; }
uint64_t HomaHeader::GetPktOffset() const { return m_pkt_offset; }
void HomaHeader::SetPktLength(uint32_t len) { m_pkt_length = len; }
uint32_t HomaHeader::GetPktLength() const { return m_pkt_length; }
void HomaHeader::SetUnscheduledBytes(uint64_t b) { m_unscheduled_bytes = b; }
uint64_t HomaHeader::GetUnscheduledBytes() const { return m_unscheduled_bytes; }
void HomaHeader::SetPriority(uint8_t p) { m_priority = p; }
uint8_t HomaHeader::GetPriority() const { return m_priority; }

void HomaHeader::SetGrantedOffset(uint64_t off) { m_granted_offset = off; }
uint64_t HomaHeader::GetGrantedOffset() const { return m_granted_offset; }
void HomaHeader::SetGrantPriority(uint8_t p) { m_grant_priority = p; }
uint8_t HomaHeader::GetGrantPriority() const { return m_grant_priority; }

void HomaHeader::SetResendOffset(uint64_t off) { m_resend_offset = off; }
uint64_t HomaHeader::GetResendOffset() const { return m_resend_offset; }
void HomaHeader::SetResendLength(uint64_t len) { m_resend_length = len; }
uint64_t HomaHeader::GetResendLength() const { return m_resend_length; }
void HomaHeader::SetRestartPriority(uint8_t p) { m_restart_priority = p; }
uint8_t HomaHeader::GetRestartPriority() const { return m_restart_priority; }

TypeId HomaHeader::GetTypeId(void) {
    static TypeId tid = TypeId("ns3::HomaHeader")
                            .SetParent<Header>()
                            .AddConstructor<HomaHeader>();
    return tid;
}

TypeId HomaHeader::GetInstanceTypeId(void) const { return GetTypeId(); }

void HomaHeader::Print(std::ostream &os) const {
    os << "HomaHeader: type=" << (uint32_t)m_type
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

uint32_t HomaHeader::GetSerializedSize(void) const { return GetHeaderSize(); }

uint32_t HomaHeader::GetHeaderSize(void) {
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

void HomaHeader::Serialize(Buffer::Iterator start) const {
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

uint32_t HomaHeader::Deserialize(Buffer::Iterator start) {
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
