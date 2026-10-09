import type { RecordType, RoutingPolicy } from "@/lib/api/types";

interface RecordTypeInfo {
  value: RecordType;
  /** Label of the option in the "Record type" select, as in the console. */
  label: string;
  /** Example shown as the placeholder of the "Value" field. */
  placeholder: string;
}

/** The record types that can be created, in the order of the console's select. */
export const recordTypes: RecordTypeInfo[] = [
  {
    value: "A",
    label: "A – Routes traffic to an IPv4 address and some AWS resources",
    placeholder: "192.0.2.235",
  },
  {
    value: "AAAA",
    label: "AAAA – Routes traffic to an IPv6 address and some AWS resources",
    placeholder: "2001:0db8:85a3:0:0:8a2e:0370:7334",
  },
  {
    value: "CNAME",
    label: "CNAME – Routes traffic to another domain name and to some AWS resources",
    placeholder: "www.example.com",
  },
  { value: "MX", label: "MX – Specifies mail servers", placeholder: "10 mailserver.example.com" },
  {
    value: "TXT",
    label: "TXT – Used to verify email senders and for application-specific values",
    placeholder: '"Sample Text Entries"',
  },
  {
    value: "PTR",
    label: "PTR – Maps an IP address to a domain name",
    placeholder: "www.example.com",
  },
  {
    value: "SRV",
    label: "SRV – Application-specific values that identify servers",
    placeholder: "1 10 5269 xmpp-server.example.com",
  },
  {
    value: "SPF",
    label: "SPF – Not recommended",
    placeholder: '"v=spf1 ip4:192.168.0.1/16 -all"',
  },
  {
    value: "NAPTR",
    label: "NAPTR – Used by DDDS applications",
    placeholder: '100 50 "u" "E2U+sip" "!^.*$!sip:information@example.com!i" .',
  },
  {
    value: "CAA",
    label: "CAA – Restricts CAs that can create SSL/TLS certificates for the domain",
    placeholder: '0 issue "amazon.com"',
  },
  { value: "NS", label: "NS – Name servers for a hosted zone", placeholder: "ns1.amazon.com" },
  {
    value: "DS",
    label: "DS - Delegation Signer, used to establish a chain of trust for DNSSEC",
    placeholder: "12345 3 1 123456789abcdef67890123456789abcdef67890",
  },
  {
    value: "TLSA",
    label:
      "TLSA - Associates a TLS server certificate or public key with the domain name. DNSSEC required.",
    placeholder: "3 1 1 d2abde240d7cd3ee6b4b28c54df034b97983a1d16e8a410e4561cb106618e971",
  },
  {
    value: "SSHFP",
    label: "SSHFP - Specifies the SSH key fingerprint and algorithm. DNSSEC required.",
    placeholder: "1 1 09F6A01D2175742B257C6B98B7C72C44C4040683",
  },
  {
    value: "HTTPS",
    label:
      "HTTPS - Provides connection optimization details like protocols, ports, and endpoints for efficient client-service communication.",
    placeholder: '1 . alpn="h3,h2" ipv4hint="192.0.2.1"',
  },
  {
    value: "SVCB",
    label: "SVCB - Delivers extensible configuration information for accessing service endpoints.",
    placeholder: '1 svc.example.com. alpn="h2" port=8443',
  },
];

/** SOA exists once per zone and can be edited but never created. */
export const soaType: RecordTypeInfo = {
  value: "SOA",
  label: "SOA – Start of authority record for a hosted zone",
  placeholder: "ns1.amazon.com. hostmaster.amazon.com. 1 7200 900 1209600 86400",
};

const UNSUPPORTED = "Not supported in this clone";

interface SelectOption {
  value: string;
  label: string;
  disabled?: boolean;
  disabledReason?: string;
}

/** The "Record type" select: every type the console lists, in its order. */
export const recordTypeOptions: SelectOption[] = recordTypes.map(({ value, label }) => ({
  value,
  label,
}));

export function recordTypeInfo(type: RecordType): RecordTypeInfo {
  return recordTypes.find((candidate) => candidate.value === type) ?? soaType;
}

/** Every type the records table can filter by, in the console's order. */
export const filterableRecordTypes: RecordType[] = [
  ...recordTypes.map((type) => type.value),
  "SOA",
];

interface RoutingPolicyInfo {
  value: RoutingPolicy;
  /** Label in the create-record select. */
  label: string;
  /** Label in the records table and its filter. */
  shortLabel: string;
}

export const routingPolicies: RoutingPolicyInfo[] = [
  { value: "simple", label: "Simple routing", shortLabel: "Simple" },
  { value: "weighted", label: "Weighted", shortLabel: "Weighted" },
  { value: "geolocation", label: "Geolocation", shortLabel: "Geolocation" },
  { value: "latency", label: "Latency", shortLabel: "Latency" },
  { value: "failover", label: "Failover", shortLabel: "Failover" },
  { value: "multivalue", label: "Multivalue answer", shortLabel: "Multivalue answer" },
];

/** The "Routing policy" select, ending with the two policies the clone does not implement. */
export const routingPolicyOptions: SelectOption[] = [
  ...routingPolicies.map(({ value, label }) => ({ value, label })),
  ...["IP-based", "Geoproximity"].map((label) => ({
    value: label,
    label,
    disabled: true,
    disabledReason: UNSUPPORTED,
  })),
];

export const TTL_PRESETS = [
  { label: "1m", seconds: 60 },
  { label: "1h", seconds: 3600 },
  { label: "1d", seconds: 86400 },
] as const;

export const DEFAULT_TTL = 300;
