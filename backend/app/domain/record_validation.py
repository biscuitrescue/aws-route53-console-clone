"""Per-type validation of resource record values, with Route 53's error wording."""

import ipaddress
import re
from collections.abc import Callable

from app.domain.dns_names import DnsNameError, validate_hostname
from app.domain.enums import RecordType

MAX_TTL = 2_147_483_647
MAX_CHARACTER_STRING_LENGTH = 255
MAX_VALUE_LENGTH = 4000
MAX_UINT16 = 65_535
MAX_UINT8 = 255

_CAA_TAG_RE = re.compile(r"^[a-z0-9]+$")
_HEX_RE = re.compile(r"^[0-9A-Fa-f]+$")
_NAPTR_FLAGS_RE = re.compile(r"^[A-Za-z0-9]*$")
_BASE64_RE = re.compile(r"^[A-Za-z0-9+/]+={0,2}$")
_SVC_GENERIC_KEY_RE = re.compile(r"^key(0|[1-9]\d{0,4})$")
# One service parameter: `key`, `key=value` or `key="value"`, up to the next whitespace.
_SVC_PARAMETER_RE = re.compile(
    r'(?P<key>[a-z0-9-]+)(?:=(?:"(?P<quoted>(?:[^"\\]|\\.)*)"|(?P<bare>[^\s"]+)))?(?=\s|$)'
)

# Digest type -> length of the digest in hexadecimal digits (RFC 4034, 4509, 6605).
_DS_DIGEST_LENGTHS = {1: 40, 2: 64, 4: 96}
# Fingerprint type -> length in hexadecimal digits (RFC 4255, 6594).
_SSHFP_FINGERPRINT_LENGTHS = {1: 40, 2: 64}
_SSHFP_ALGORITHMS = frozenset({1, 2, 3, 4, 6})
# Matching type -> length of the association data in hexadecimal digits (RFC 6698).
_TLSA_DATA_LENGTHS = {1: 64, 2: 128}
_ESCAPED_OCTET_RE = re.compile(r"\\(\d{3}|.)")


class RecordValueError(ValueError):
    """Raised when a record value does not match its type's format."""


def _fatal(code: str, description: str, value: str) -> RecordValueError:
    return RecordValueError(
        f"Invalid Resource Record: 'FATAL problem: {code} ({description}) "
        f"encountered with '{value}''"
    )


def _uint(text: str, maximum: int) -> int | None:
    if not text.isdigit():
        return None
    number = int(text)
    return number if number <= maximum else None


def _is_hostname(value: str, *, allow_root: bool = False) -> bool:
    try:
        validate_hostname(value, allow_root=allow_root)
    except DnsNameError:
        return False
    return True


def parse_character_strings(value: str) -> list[str]:
    """Split TXT-style data into its quoted strings; raises if anything is unquoted."""
    strings: list[str] = []
    position, length = 0, len(value)
    while position < length:
        if value[position].isspace():
            position += 1
            continue
        if value[position] != '"':
            raise _fatal(
                "InvalidCharacterString", "Value should be enclosed in quotation marks", value
            )
        end = position + 1
        while end < length and value[end] != '"':
            end += 2 if value[end] == "\\" else 1
        if end >= length:
            raise _fatal(
                "InvalidCharacterString", "Value should be enclosed in quotation marks", value
            )
        strings.append(value[position + 1 : end])
        position = end + 1
    return strings


def _validate_a(value: str) -> None:
    try:
        ipaddress.IPv4Address(value)
    except ValueError:
        raise _fatal(
            "ARRDATAIllegalIPv4Address", "Value is not a valid IPv4 address", value
        ) from None


def _validate_aaaa(value: str) -> None:
    try:
        ipaddress.IPv6Address(value)
    except ValueError:
        raise _fatal(
            "AAAARRDATAIllegalIPv6Address", "Value is not a valid IPv6 address", value
        ) from None


def _validate_host(value: str) -> None:
    if not _is_hostname(value):
        raise _fatal("DomainNameInvalid", "Value is not a valid domain name", value)


def _validate_mx(value: str) -> None:
    fields = value.split()
    if len(fields) != 2:
        raise _fatal("MXRRDATANotTwoFields", "MX record doesn't have 2 fields", value)
    if _uint(fields[0], MAX_UINT16) is None:
        raise _fatal("MXRRDATAIllegalPriority", "MX priority must be between 0 and 65535", value)
    if not _is_hostname(fields[1], allow_root=True):
        raise _fatal("DomainNameInvalid", "Value is not a valid domain name", value)


def _validate_srv(value: str) -> None:
    fields = value.split()
    if len(fields) != 4:
        raise _fatal("SRVRRDATANotFourFields", "SRV record doesn't have 4 fields", value)
    if any(_uint(field, MAX_UINT16) is None for field in fields[:3]):
        raise _fatal(
            "SRVRRDATAIllegalNumber",
            "SRV priority, weight and port must be between 0 and 65535",
            value,
        )
    if not _is_hostname(fields[3], allow_root=True):
        raise _fatal("DomainNameInvalid", "Value is not a valid domain name", value)


def _validate_caa(value: str) -> None:
    fields = value.split(maxsplit=2)
    if len(fields) != 3:
        raise _fatal("CAARRDATANotThreeFields", "CAA record doesn't have 3 fields", value)
    flags, tag, data = fields
    if _uint(flags, MAX_UINT8) is None:
        raise _fatal("CAARRDATAIllegalFlags", "CAA flags must be between 0 and 255", value)
    if not _CAA_TAG_RE.match(tag):
        raise _fatal("CAARRDATAIllegalTag", "CAA tag must be alphanumeric lowercase", value)
    if len(parse_character_strings(data)) != 1:
        raise _fatal("InvalidCharacterString", "Value should be enclosed in quotation marks", value)


def _validate_txt(value: str) -> None:
    strings = parse_character_strings(value)
    if not strings:
        raise _fatal("InvalidCharacterString", "Value should be enclosed in quotation marks", value)
    for string in strings:
        if len(_ESCAPED_OCTET_RE.sub("x", string)) > MAX_CHARACTER_STRING_LENGTH:
            raise RecordValueError(
                "Invalid Resource Record: 'FATAL problem: TXTRDATATooLong "
                "(Value is too long) encountered with a string longer than 255 characters'"
            )


def _tokens(value: str) -> list[tuple[str, bool]]:
    """Split a value on whitespace, keeping quoted strings whole: ``(text, was_quoted)``."""
    tokens: list[tuple[str, bool]] = []
    position, length = 0, len(value)
    while position < length:
        if value[position].isspace():
            position += 1
            continue
        if value[position] == '"':
            end = position + 1
            while end < length and value[end] != '"':
                end += 2 if value[end] == "\\" else 1
            if end >= length:
                raise _fatal("InvalidCharacterString", "Quotation marks are not balanced", value)
            tokens.append((value[position + 1 : end], True))
            position = end + 1
        else:
            end = position
            while end < length and not value[end].isspace():
                end += 1
            tokens.append((value[position:end], False))
            position = end
    return tokens


def _is_hex(text: str, length: int | None = None) -> bool:
    if not _HEX_RE.match(text) or len(text) % 2:
        return False
    return length is None or len(text) == length


def _validate_naptr(value: str) -> None:
    tokens = _tokens(value)
    if len(tokens) != 6:
        raise _fatal("NAPTRRRDATANotSixFields", "NAPTR record doesn't have 6 fields", value)
    (order, _), (preference, _), flags, service, regexp, (replacement, replacement_quoted) = tokens
    if _uint(order, MAX_UINT16) is None or _uint(preference, MAX_UINT16) is None:
        raise _fatal(
            "NAPTRRRDATAIllegalNumber",
            "NAPTR order and preference must be between 0 and 65535",
            value,
        )
    if not all(quoted for _, quoted in (flags, service, regexp)):
        raise _fatal(
            "InvalidCharacterString",
            "NAPTR flags, service and regexp should be enclosed in quotation marks",
            value,
        )
    if not _NAPTR_FLAGS_RE.match(flags[0]):
        raise _fatal("NAPTRRRDATAIllegalFlags", "NAPTR flags must be letters or digits", value)
    if any(len(text) > MAX_CHARACTER_STRING_LENGTH for text, _ in (flags, service, regexp)):
        raise _fatal("NAPTRRRDATATooLong", "A NAPTR field is longer than 255 characters", value)
    if replacement_quoted or not _is_hostname(replacement, allow_root=True):
        raise _fatal("DomainNameInvalid", "NAPTR replacement is not a valid domain name", value)


def _validate_ds(value: str) -> None:
    fields = value.split()
    if len(fields) != 4:
        raise _fatal("DSRRDATANotFourFields", "DS record doesn't have 4 fields", value)
    key_tag, algorithm, digest_type, digest = fields
    if _uint(key_tag, MAX_UINT16) is None:
        raise _fatal("DSRRDATAIllegalKeyTag", "DS key tag must be between 0 and 65535", value)
    if _uint(algorithm, MAX_UINT8) is None:
        raise _fatal("DSRRDATAIllegalAlgorithm", "DS algorithm must be between 0 and 255", value)
    length = _DS_DIGEST_LENGTHS.get(_uint(digest_type, MAX_UINT8) or 0)
    if length is None:
        raise _fatal("DSRRDATAIllegalDigestType", "DS digest type must be 1, 2 or 4", value)
    if not _is_hex(digest, length):
        raise _fatal(
            "DSRRDATAIllegalDigest",
            f"DS digest must be {length} hexadecimal digits for digest type {digest_type}",
            value,
        )


def _validate_tlsa(value: str) -> None:
    fields = value.split()
    if len(fields) != 4:
        raise _fatal("TLSARRDATANotFourFields", "TLSA record doesn't have 4 fields", value)
    usage, selector, matching_type, data = fields
    if (_uint(usage, 3)) is None:
        raise _fatal("TLSARRDATAIllegalUsage", "TLSA certificate usage must be 0 to 3", value)
    if _uint(selector, 1) is None:
        raise _fatal("TLSARRDATAIllegalSelector", "TLSA selector must be 0 or 1", value)
    matching = _uint(matching_type, 2)
    if matching is None:
        raise _fatal("TLSARRDATAIllegalMatchingType", "TLSA matching type must be 0, 1 or 2", value)
    length = _TLSA_DATA_LENGTHS.get(matching)
    if not _is_hex(data, length):
        expected = "an even number of" if length is None else str(length)
        raise _fatal(
            "TLSARRDATAIllegalData",
            f"TLSA certificate association data must be {expected} hexadecimal digits",
            value,
        )


def _validate_sshfp(value: str) -> None:
    fields = value.split()
    if len(fields) != 3:
        raise _fatal("SSHFPRRDATANotThreeFields", "SSHFP record doesn't have 3 fields", value)
    algorithm, fingerprint_type, fingerprint = fields
    if _uint(algorithm, MAX_UINT8) not in _SSHFP_ALGORITHMS:
        raise _fatal(
            "SSHFPRRDATAIllegalAlgorithm", "SSHFP algorithm must be 1, 2, 3, 4 or 6", value
        )
    length = _SSHFP_FINGERPRINT_LENGTHS.get(_uint(fingerprint_type, MAX_UINT8) or 0)
    if length is None:
        raise _fatal("SSHFPRRDATAIllegalType", "SSHFP fingerprint type must be 1 or 2", value)
    if not _is_hex(fingerprint, length):
        raise _fatal(
            "SSHFPRRDATAIllegalFingerprint",
            f"SSHFP fingerprint must be {length} hexadecimal digits for type {fingerprint_type}",
            value,
        )


def _addresses(text: str, parse: Callable[[str], object]) -> bool:
    parts = text.split(",")
    try:
        for part in parts:
            parse(part)
    except ValueError:
        return False
    return bool(text)


def _svc_parameter_problem(key: str, text: str | None) -> str | None:
    """Why a service parameter is not valid, or ``None`` when it is."""
    match key:
        case "no-default-alpn":
            return "no-default-alpn takes no value" if text is not None else None
        case "alpn" | "mandatory":
            ok = text is not None and all(text.split(","))
            return None if ok else f"{key} must be a comma-separated list"
        case "port":
            ok = text is not None and _uint(text, MAX_UINT16) is not None
            return None if ok else "port must be between 0 and 65535"
        case "ipv4hint":
            ok = text is not None and _addresses(text, ipaddress.IPv4Address)
            return None if ok else "ipv4hint must be a comma-separated list of IPv4 addresses"
        case "ipv6hint":
            ok = text is not None and _addresses(text, ipaddress.IPv6Address)
            return None if ok else "ipv6hint must be a comma-separated list of IPv6 addresses"
        case "ech":
            ok = text is not None and _BASE64_RE.match(text) is not None
            return None if ok else "ech must be base64"
        case _ if _SVC_GENERIC_KEY_RE.match(key) and int(key[3:]) <= MAX_UINT16:
            return None
        case _:
            return f"'{key}' is not a service parameter"


def _validate_svcb(value: str) -> None:
    """SVCB and HTTPS: ``priority target [key[=value] ...]`` (RFC 9460)."""
    fields = value.split(maxsplit=2)
    if len(fields) < 2:
        raise _fatal("SVCBRRDATATooFewFields", "Record needs a priority and a target", value)
    priority = _uint(fields[0], MAX_UINT16)
    if priority is None:
        raise _fatal("SVCBRRDATAIllegalPriority", "Priority must be between 0 and 65535", value)
    if not _is_hostname(fields[1], allow_root=True):
        raise _fatal("DomainNameInvalid", "Target is not a valid domain name", value)

    parameters = fields[2] if len(fields) == 3 else ""
    if priority == 0 and parameters.strip():
        raise _fatal(
            "SVCBRRDATAAliasModeParameters",
            "A record with priority 0 is an alias and takes no parameters",
            value,
        )
    seen: set[str] = set()
    position = 0
    while position < len(parameters):
        if parameters[position].isspace():
            position += 1
            continue
        match = _SVC_PARAMETER_RE.match(parameters, position)
        if match is None:
            raise _fatal("SVCBRRDATAIllegalParameter", "Parameters must be key or key=value", value)
        position = match.end()
        key = match["key"]
        if key in seen:
            raise _fatal("SVCBRRDATADuplicateParameter", f"'{key}' is given twice", value)
        seen.add(key)
        text = match["quoted"] if match["quoted"] is not None else match["bare"]
        problem = _svc_parameter_problem(key, text)
        if problem:
            raise _fatal("SVCBRRDATAIllegalParameter", problem, value)


def _validate_soa(value: str) -> None:
    fields = value.split()
    if len(fields) != 7:
        raise _fatal("SOARRDATANotSevenFields", "SOA record doesn't have 7 fields", value)
    if not all(_is_hostname(field) for field in fields[:2]):
        raise _fatal("DomainNameInvalid", "Value is not a valid domain name", value)
    if any(_uint(field, MAX_TTL) is None for field in fields[2:]):
        raise _fatal("SOARRDATAIllegalNumber", "SOA timers must be non-negative integers", value)


_VALIDATORS: dict[RecordType, Callable[[str], None]] = {
    RecordType.A: _validate_a,
    RecordType.AAAA: _validate_aaaa,
    RecordType.CAA: _validate_caa,
    RecordType.CNAME: _validate_host,
    RecordType.DS: _validate_ds,
    RecordType.HTTPS: _validate_svcb,
    RecordType.MX: _validate_mx,
    RecordType.NAPTR: _validate_naptr,
    RecordType.NS: _validate_host,
    RecordType.PTR: _validate_host,
    RecordType.SOA: _validate_soa,
    # SPF records carry the same data as TXT (RFC 7208 retired the type, Route 53 keeps it).
    RecordType.SPF: _validate_txt,
    RecordType.SRV: _validate_srv,
    RecordType.SSHFP: _validate_sshfp,
    RecordType.SVCB: _validate_svcb,
    RecordType.TLSA: _validate_tlsa,
    RecordType.TXT: _validate_txt,
}

_SINGLE_VALUE_TYPES = frozenset({RecordType.CNAME, RecordType.SOA})


def validate_values(record_type: RecordType, values: list[str]) -> list[str]:
    """Validate and tidy the values of a record set; returns the cleaned list."""
    cleaned = [value.strip() for value in values if value.strip()]
    if not cleaned:
        raise RecordValueError("At least one value is required")
    if record_type in _SINGLE_VALUE_TYPES and len(cleaned) > 1:
        raise RecordValueError(f"{record_type} records can have only one value")
    if len(set(cleaned)) != len(cleaned):
        raise RecordValueError(
            "Invalid Resource Record: 'Duplicate Resource Record: "
            f"'{next(v for v in cleaned if cleaned.count(v) > 1)}''"
        )

    validate = _VALIDATORS[record_type]
    for value in cleaned:
        if len(value) > MAX_VALUE_LENGTH:
            raise RecordValueError(f"Value is too long (maximum {MAX_VALUE_LENGTH} characters)")
        validate(value)
    return cleaned
