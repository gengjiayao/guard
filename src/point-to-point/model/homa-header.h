#ifndef HOMA_HEADER_H
#define HOMA_HEADER_H

#include "ns3/header.h"

namespace ns3 {

// HomaHeader: per-packet header for the standard Homa implementation
// (cc_mode = 12). Carries a packet type plus the union of fields used by
// each type. Fields not relevant to the current type are unset / ignored.
class HomaHeader : public Header {
public:
    enum Type : uint8_t {
        DATA = 0,
        GRANT = 1,
        RESEND = 2,
        BUSY = 3,
        NEED_ACK = 4,
        ACK = 5,
        UNKNOWN = 6,
    };

    HomaHeader();

    // common
    void SetType(uint8_t t);
    uint8_t GetType() const;
    void SetMessageId(uint64_t id);
    uint64_t GetMessageId() const;

    // DATA
    void SetMsgTotalLength(uint64_t len);
    uint64_t GetMsgTotalLength() const;
    void SetPktOffset(uint64_t off);
    uint64_t GetPktOffset() const;
    void SetPktLength(uint32_t len);
    uint32_t GetPktLength() const;
    void SetUnscheduledBytes(uint64_t b);
    uint64_t GetUnscheduledBytes() const;
    void SetPriority(uint8_t p);
    uint8_t GetPriority() const;

    // GRANT
    void SetGrantedOffset(uint64_t off);
    uint64_t GetGrantedOffset() const;
    void SetGrantPriority(uint8_t p);
    uint8_t GetGrantPriority() const;

    // RESEND
    void SetResendOffset(uint64_t off);
    uint64_t GetResendOffset() const;
    void SetResendLength(uint64_t len);
    uint64_t GetResendLength() const;
    void SetRestartPriority(uint8_t p);
    uint8_t GetRestartPriority() const;

    static TypeId GetTypeId(void);
    virtual TypeId GetInstanceTypeId(void) const;
    virtual void Print(std::ostream &os) const;
    virtual uint32_t GetSerializedSize(void) const;
    static uint32_t GetHeaderSize(void);

private:
    virtual void Serialize(Buffer::Iterator start) const;
    virtual uint32_t Deserialize(Buffer::Iterator start);

    uint8_t  m_type;
    uint64_t m_message_id;
    // DATA
    uint64_t m_msg_total_length;
    uint64_t m_pkt_offset;
    uint32_t m_pkt_length;
    uint64_t m_unscheduled_bytes;
    uint8_t  m_priority;
    // GRANT
    uint64_t m_granted_offset;
    uint8_t  m_grant_priority;
    // RESEND
    uint64_t m_resend_offset;
    uint64_t m_resend_length;
    uint8_t  m_restart_priority;
};

} // namespace ns3

#endif
