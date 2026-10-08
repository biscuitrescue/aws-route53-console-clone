import pytest

from app.domain.enums import RecordType
from app.domain.zonefile import (
    ZoneFileRecord,
    parse_zone_file,
    render_zone_file,
    to_zone_file_value,
)

ZONE = "example.com."

ZONE_FILE = """\
$ORIGIN example.com.
$TTL 1h
@   IN  SOA ns1.example.com. hostmaster.example.com. (
            2024010101 ; serial
            2h         ; refresh
            15m        ; retry
            2w         ; expire
            1d )       ; minimum
@           IN  NS    ns1
@           IN  NS    ns2.example.net.
@           300 IN A  192.0.2.10
www         IN  A     192.0.2.10
            IN  A     192.0.2.11
www         IN  AAAA  2001:db8::10
blog  600   IN  CNAME www
@           IN  MX    10 mail
@           IN  TXT   "v=spf1 include:_spf.example.com ~all"
long        IN  TXT   ( "first part; not a comment"
                        "second part" )
_sip._tcp   IN  SRV   10 60 5060 sip.example.com.
@           IN  CAA   0 issue "amazon.com"
*.dev       IN  A     192.0.2.99
"""


def _by_key(text: str) -> dict[tuple[str, str], tuple[int, list[str]]]:
    parsed = parse_zone_file(text, ZONE)
    assert parsed.issues == []
    return {(rs.name, rs.type.value): (rs.ttl, rs.values) for rs in parsed.record_sets}


def test_parses_every_supported_record_type() -> None:
    records = _by_key(ZONE_FILE)
    assert records[("example.com.", "SOA")] == (
        3600,
        ["ns1.example.com. hostmaster.example.com. 2024010101 7200 900 1209600 86400"],
    )
    assert records[("example.com.", "NS")] == (3600, ["ns1.example.com.", "ns2.example.net."])
    assert records[("example.com.", "A")] == (300, ["192.0.2.10"])
    assert records[("www.example.com.", "A")] == (3600, ["192.0.2.10", "192.0.2.11"])
    assert records[("www.example.com.", "AAAA")] == (3600, ["2001:db8::10"])
    assert records[("blog.example.com.", "CNAME")] == (600, ["www.example.com."])
    assert records[("example.com.", "MX")] == (3600, ["10 mail.example.com."])
    assert records[("example.com.", "TXT")] == (
        3600,
        ['"v=spf1 include:_spf.example.com ~all"'],
    )
    assert records[("long.example.com.", "TXT")] == (
        3600,
        ['"first part; not a comment" "second part"'],
    )
    assert records[("_sip._tcp.example.com.", "SRV")] == (3600, ["10 60 5060 sip.example.com."])
    assert records[("example.com.", "CAA")] == (3600, ['0 issue "amazon.com"'])
    assert records[("*.dev.example.com.", "A")] == (3600, ["192.0.2.99"])


def test_origin_directive_changes_relative_names() -> None:
    records = _by_key("$ORIGIN sub.example.com.\nhost 60 IN A 192.0.2.1\n@ 60 IN A 192.0.2.2\n")
    assert records == {
        ("host.sub.example.com.", "A"): (60, ["192.0.2.1"]),
        ("sub.example.com.", "A"): (60, ["192.0.2.2"]),
    }


def test_ttl_and_class_may_appear_in_either_order() -> None:
    records = _by_key("a IN 120 A 192.0.2.1\nb 120 IN A 192.0.2.2\nc 120 A 192.0.2.3\n")
    assert {ttl for ttl, _values in records.values()} == {120}


def test_ttl_falls_back_to_the_previous_record_then_the_default() -> None:
    records = _by_key("a A 192.0.2.1\nb 2h A 192.0.2.2\nc A 192.0.2.3\n")
    assert records[("a.example.com.", "A")][0] == 300
    assert records[("b.example.com.", "A")][0] == 7200
    assert records[("c.example.com.", "A")][0] == 7200


def test_unquoted_txt_data_is_quoted() -> None:
    records = _by_key("note 60 IN TXT hello world\n")
    assert records[("note.example.com.", "TXT")] == (60, ['"hello" "world"'])


@pytest.mark.parametrize(
    ("text", "message"),
    [
        ("www 300 IN A 999.1.1.1\n", "not a valid IPv4 address"),
        ("www 300 IN HINFO cpu os\n", "Record type HINFO is not supported"),
        ("www 300 CH A 192.0.2.1\n", "Class CH is not supported"),
        ("www 300 IN MX mail\n", "MX record data must have 2 fields"),
        ("www 300 IN\n", "Record is missing a type"),
        ("www 300 IN A\n", "A record has no data"),
        ("www.example.org. 300 IN A 192.0.2.1\n", "not permitted in zone example.com."),
        ('www 300 IN TXT "unterminated\n', "Unterminated quoted string"),
        ("www 300 IN A 192.0.2.1 )\n", "Unbalanced closing parenthesis"),
        ('www 300 IN TXT ( "a"\n', "Unbalanced opening parenthesis"),
        ("$INCLUDE other.zone\n", "Directive $INCLUDE is not supported"),
        ("$TTL soon\n", "Invalid TTL 'soon'"),
    ],
)
def test_problems_are_reported_with_their_line(text: str, message: str) -> None:
    parsed = parse_zone_file(f"ok 300 IN A 192.0.2.1\n{text}", ZONE)
    assert [issue.line for issue in parsed.issues] == [2]
    assert message in parsed.issues[0].message
    assert [rs.name for rs in parsed.record_sets] == ["ok.example.com."]


def test_a_record_cannot_inherit_an_owner_before_one_is_named() -> None:
    parsed = parse_zone_file("  300 IN A 192.0.2.1\n", ZONE)
    assert [(issue.line, issue.message) for issue in parsed.issues] == [
        (1, "Record has no owner name")
    ]


def test_every_bad_line_is_reported() -> None:
    parsed = parse_zone_file("a 60 IN A bad\nb 60 IN A 192.0.2.1\nc 60 IN AAAA bad\n", ZONE)
    assert [issue.line for issue in parsed.issues] == [1, 3]
    assert len(parsed.record_sets) == 1


@pytest.mark.parametrize(
    ("record_type", "value", "expected"),
    [
        (RecordType.CNAME, "www.example.com", "www.example.com."),
        (RecordType.MX, "10 Mail.Example.com", "10 mail.example.com."),
        (RecordType.SRV, "10 60 5060 sip.example.com", "10 60 5060 sip.example.com."),
        (RecordType.NS, "ns1.example.net.", "ns1.example.net."),
        (RecordType.A, "192.0.2.1", "192.0.2.1"),
        (RecordType.TXT, '"keep as is"', '"keep as is"'),
    ],
)
def test_host_names_become_absolute_on_export(
    record_type: RecordType, value: str, expected: str
) -> None:
    assert to_zone_file_value(record_type, value) == expected


def test_render_then_parse_round_trips() -> None:
    records = [
        ZoneFileRecord("example.com.", RecordType.A, 300, ("192.0.2.10",)),
        ZoneFileRecord("example.com.", RecordType.MX, 3600, ("10 mail.example.com.",)),
        ZoneFileRecord("example.com.", RecordType.TXT, 300, ('"v=spf1 ~all"', '"a; b" "c"')),
        ZoneFileRecord("www.example.com.", RecordType.A, 60, ("192.0.2.1", "192.0.2.2")),
        ZoneFileRecord("blog.example.com.", RecordType.CNAME, 300, ("www.example.com.",)),
        ZoneFileRecord(
            "_sip._tcp.example.com.", RecordType.SRV, 300, ("1 2 5060 sip.example.com.",)
        ),
        ZoneFileRecord("example.com.", RecordType.CAA, 300, ('0 issue "amazon.com"',)),
        ZoneFileRecord("*.dev.example.com.", RecordType.AAAA, 300, ("2001:db8::1",)),
    ]
    text = render_zone_file(ZONE, records, comments=["exported for a test"])
    assert text.startswith("; exported for a test\n$ORIGIN example.com.\n")

    parsed = parse_zone_file(text, ZONE)
    assert parsed.issues == []
    assert [
        ZoneFileRecord(rs.name, rs.type, rs.ttl, tuple(rs.values)) for rs in parsed.record_sets
    ] == records
