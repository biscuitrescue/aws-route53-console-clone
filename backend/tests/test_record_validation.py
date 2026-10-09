import pytest

from app.domain.enums import RecordType
from app.domain.record_validation import (
    RecordValueError,
    parse_character_strings,
    validate_values,
)

VALID: list[tuple[RecordType, list[str]]] = [
    (RecordType.A, ["192.0.2.10"]),
    (RecordType.A, ["192.0.2.10", "192.0.2.11"]),
    (RecordType.AAAA, ["2001:db8::10"]),
    (RecordType.AAAA, ["::1", "2001:0db8:85a3:0000:0000:8a2e:0370:7334"]),
    (RecordType.CNAME, ["www.example.com"]),
    (RecordType.CNAME, ["www.example.com."]),
    (RecordType.TXT, ['"v=spf1 include:_spf.example.com ~all"']),
    (RecordType.TXT, ['"part one" "part two"']),
    (RecordType.TXT, ['"with \\" escaped quote"']),
    (RecordType.TXT, [f'"{"a" * 255}"']),
    (RecordType.MX, ["10 mail.example.com"]),
    (RecordType.MX, ["0 ."]),
    (RecordType.NS, ["ns-1.example.net", "ns-2.example.net."]),
    (RecordType.PTR, ["www.example.com"]),
    (RecordType.SRV, ["10 60 5060 sip.example.com"]),
    (RecordType.SRV, ["0 0 0 ."]),
    (RecordType.CAA, ['0 issue "amazon.com"']),
    (RecordType.CAA, ['128 issuewild ";"']),
    (
        RecordType.SOA,
        ["ns-1.awsdns-00.com. awsdns-hostmaster.amazon.com. 1 7200 900 1209600 86400"],
    ),
]

INVALID: list[tuple[RecordType, list[str], str]] = [
    (RecordType.A, ["999.1.1.1"], "ARRDATAIllegalIPv4Address"),
    (RecordType.A, ["192.0.2"], "not a valid IPv4 address"),
    (RecordType.A, ["2001:db8::10"], "not a valid IPv4 address"),
    (RecordType.A, ["192.0.2.010"], "not a valid IPv4 address"),
    (RecordType.AAAA, ["192.0.2.10"], "AAAARRDATAIllegalIPv6Address"),
    (RecordType.AAAA, ["2001:db8::g"], "not a valid IPv6 address"),
    (RecordType.CNAME, ["bad..host"], "not a valid domain name"),
    (RecordType.CNAME, ["a.example.com", "b.example.com"], "only one value"),
    (RecordType.TXT, ["no quotes"], "enclosed in quotation marks"),
    (RecordType.TXT, ['"unterminated'], "enclosed in quotation marks"),
    (RecordType.TXT, ['"ok" trailing'], "enclosed in quotation marks"),
    (RecordType.TXT, [f'"{"a" * 256}"'], "TXTRDATATooLong"),
    (RecordType.MX, ["mail.example.com"], "MX record doesn't have 2 fields"),
    (RecordType.MX, ["70000 mail.example.com"], "MX priority"),
    (RecordType.MX, ["ten mail.example.com"], "MX priority"),
    (RecordType.MX, ["10 bad..host"], "not a valid domain name"),
    (RecordType.NS, ["not a host"], "not a valid domain name"),
    (RecordType.PTR, ["has space.example.com"], "not a valid domain name"),
    (RecordType.SRV, ["10 60 sip.example.com"], "SRV record doesn't have 4 fields"),
    (RecordType.SRV, ["10 60 99999 sip.example.com"], "between 0 and 65535"),
    (RecordType.CAA, ["0 issue"], "CAA record doesn't have 3 fields"),
    (RecordType.CAA, ['256 issue "amazon.com"'], "CAA flags"),
    (RecordType.CAA, ['0 Issue! "amazon.com"'], "CAA tag"),
    (RecordType.CAA, ["0 issue amazon.com"], "enclosed in quotation marks"),
    (RecordType.SOA, ["ns.example.com. host.example.com. 1 2 3"], "SOA record doesn't have 7"),
    (RecordType.A, [], "At least one value is required"),
    (RecordType.A, ["  ", ""], "At least one value is required"),
    (RecordType.A, ["192.0.2.1", "192.0.2.1"], "Duplicate Resource Record"),
]


@pytest.mark.parametrize(("record_type", "values"), VALID)
def test_valid_values_are_accepted(record_type: RecordType, values: list[str]) -> None:
    assert validate_values(record_type, values) == values


@pytest.mark.parametrize(("record_type", "values", "message"), INVALID)
def test_invalid_values_are_rejected(
    record_type: RecordType, values: list[str], message: str
) -> None:
    with pytest.raises(RecordValueError) as error:
        validate_values(record_type, values)
    assert message in str(error.value)


def test_values_are_trimmed_and_blank_lines_dropped() -> None:
    assert validate_values(RecordType.A, [" 192.0.2.1 ", "", "192.0.2.2"]) == [
        "192.0.2.1",
        "192.0.2.2",
    ]


def test_invalid_value_error_uses_route53_wording() -> None:
    with pytest.raises(RecordValueError) as error:
        validate_values(RecordType.A, ["999.1.1.1"])
    assert str(error.value) == (
        "Invalid Resource Record: 'FATAL problem: ARRDATAIllegalIPv4Address "
        "(Value is not a valid IPv4 address) encountered with '999.1.1.1''"
    )


def test_character_strings_are_split() -> None:
    assert parse_character_strings('"a b" "c\\"d"') == ["a b", 'c\\"d']
