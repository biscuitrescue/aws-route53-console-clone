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
    RecordType.MX: _validate_mx,
    RecordType.NS: _validate_host,
    RecordType.PTR: _validate_host,
    RecordType.SOA: _validate_soa,
    RecordType.SRV: _validate_srv,
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
