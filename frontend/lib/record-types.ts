import type { RecordType, RoutingPolicy } from "@/lib/api/types";

interface RecordTypeInfo {
  value: RecordType;
  /** Label of the option in the "Record type" select, as in the console. */
  label: string;
  /** Example shown as the placeholder of the "Value" field. */
  placeholder: string;
}

/** The record types that can be created, in the console's order. */
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
    value: "CAA",
    label: "CAA – Restricts CAs that can create SSL/TLS certificates for the domain",
    placeholder: '0 issue "amazon.com"',
  },
  { value: "NS", label: "NS – Name servers for a hosted zone", placeholder: "ns1.amazon.com" },
];

/** SOA exists once per zone and can be edited but never created. */
export const soaType: RecordTypeInfo = {
  value: "SOA",
  label: "SOA – Start of authority record for a hosted zone",
  placeholder: "ns1.amazon.com. hostmaster.amazon.com. 1 7200 900 1209600 86400",
};

const UNSUPPORTED = "Not supported in this clone";

/**
 * Types the console also lists. The clone does not store them, so the select shows them
 * disabled rather than leaving them out.
 */
const unsupportedRecordTypes = [
  { value: "SPF", label: "SPF – Not recommended" },
  { value: "NAPTR", label: "NAPTR – Used by DDDS applications" },
  {
    value: "DS",
    label: "DS - Delegation Signer, used to establish a chain of trust for DNSSEC",
  },
  {
    value: "TLSA",
    label:
      "TLSA - Associates a TLS server certificate or public key with the domain name. DNSSEC required.",
  },
  {
    value: "SSHFP",
    label: "SSHFP - Specifies the SSH key fingerprint and algorithm. DNSSEC required.",
  },
  {
    value: "HTTPS",
    label:
      "HTTPS - Provides connection optimization details like protocols, ports, and endpoints for efficient client-service communication.",
  },
  {
    value: "SVCB",
    label: "SVCB - Delivers extensible configuration information for accessing service endpoints.",
  },
];

const TYPE_ORDER = [
  "A",
  "AAAA",
  "CNAME",
  "MX",
  "TXT",
  "PTR",
  "SRV",
  "SPF",
  "NAPTR",
  "CAA",
  "NS",
  "DS",
  "TLSA",
  "SSHFP",
  "HTTPS",
  "SVCB",
];

interface SelectOption {
  value: string;
  label: string;
  disabled?: boolean;
  disabledReason?: string;
}

/** The "Record type" select: every type the console lists, in its order. */
export const recordTypeOptions: SelectOption[] = TYPE_ORDER.flatMap((value): SelectOption[] => {
  const supported = recordTypes.find((type) => type.value === value);
  if (supported) return [{ value, label: supported.label }];
  const other = unsupportedRecordTypes.find((type) => type.value === value);
  return other ? [{ ...other, disabled: true, disabledReason: UNSUPPORTED }] : [];
});

export function recordTypeInfo(type: RecordType): RecordTypeInfo {
  return recordTypes.find((candidate) => candidate.value === type) ?? soaType;
}

/** Every type the records table can filter by, in the console's order. */
export const filterableRecordTypes: RecordType[] = [
  "A",
  "AAAA",
  "CNAME",
  "MX",
  "TXT",
  "PTR",
  "SRV",
  "CAA",
  "NS",
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
