"""DS, HTTPS, NAPTR, SPF, SSHFP, SVCB and TLSA: validation, storage, import and export."""

from typing import Any

import pytest
from fastapi.testclient import TestClient

from app.domain.enums import RecordType
from app.domain.record_validation import RecordValueError, validate_values
from app.domain.zonefile import parse_zone_file
from tests.conftest import API, create_record, create_zone

SHA1 = "09f6a01d2175742b257c6b98b7c72c44c4040683"
SHA256 = "d2abde240d7cd3ee6b4b28c54df034b97983a1d16e8a410e4561cb106618e971"
SHA384 = "ab" * 48
SHA512 = "cd" * 64

# One value per type, used wherever a record of every new type is needed.
EXAMPLES: dict[str, tuple[str, list[str]]] = {
    "SPF": ("", ['"v=spf1 ip4:192.0.2.0/24 -all"']),
    "NAPTR": ("sip", ['100 10 "u" "sip+E2U" "!^.*$!sip:info@example.com!i" .']),
    "DS": ("child", [f"12345 13 2 {SHA256}"]),
    "TLSA": ("_443._tcp.www", [f"3 1 1 {SHA256}"]),
    "SSHFP": ("host", [f"4 2 {SHA256}", f"1 1 {SHA1}"]),
    "HTTPS": ("", ['1 . alpn="h3,h2" ipv4hint="192.0.2.1,192.0.2.2"']),
    "SVCB": ("_dns", ["1 doh.example.com. alpn=h2 port=443", "0 pool.example.com."]),
}

VALID: list[tuple[RecordType, str]] = [
    (RecordType.SPF, '"v=spf1 -all"'),
    (RecordType.SPF, '"part one" "part two"'),
    (RecordType.NAPTR, '100 10 "u" "sip+E2U" "!^.*$!sip:information@example.com!i" .'),
    (RecordType.NAPTR, '10 100 "S" "SIP+D2U" "" _sip._udp.example.com.'),
    (RecordType.NAPTR, '0 0 "" "" "" .'),
    (RecordType.NAPTR, '100 10 "u" "E2U+sip" "!^(\\\\+441632960083)$!sip:\\\\1@example.com!" .'),
    (RecordType.DS, f"12345 13 2 {SHA256}"),
    (RecordType.DS, f"60485 5 1 {SHA1.upper()}"),
    (RecordType.DS, f"0 255 4 {SHA384}"),
    (RecordType.TLSA, f"3 1 1 {SHA256}"),
    (RecordType.TLSA, f"2 0 2 {SHA512}"),
    (RecordType.TLSA, "0 0 0 308201"),
    (RecordType.SSHFP, f"1 1 {SHA1}"),
    (RecordType.SSHFP, f"4 2 {SHA256}"),
    (RecordType.SSHFP, f"6 2 {SHA256}"),
    (RecordType.HTTPS, "1 ."),
    (RecordType.HTTPS, "0 svc.example.net."),
    (RecordType.HTTPS, '1 . alpn="h3,h2" ipv4hint="192.0.2.1,192.0.2.2"'),
    (RecordType.HTTPS, "1 . alpn=h2 port=8443 no-default-alpn ipv6hint=2001:db8::1"),
    (RecordType.HTTPS, "16 backup.example.net mandatory=alpn alpn=h2 ech=AEX+DQBB key65000=x"),
    (RecordType.SVCB, "1 svc.example.com. port=5353"),
    (RecordType.SVCB, "0 pool.example.com."),
]

INVALID: list[tuple[RecordType, str, str]] = [
    (RecordType.SPF, "v=spf1 -all", "enclosed in quotation marks"),
    (RecordType.NAPTR, '100 10 "u" "s" ""', "doesn't have 6 fields"),
    (RecordType.NAPTR, '70000 10 "u" "s" "" .', "between 0 and 65535"),
    (RecordType.NAPTR, '100 x "u" "s" "" .', "between 0 and 65535"),
    (RecordType.NAPTR, '100 10 u "s" "" .', "enclosed in quotation marks"),
    (RecordType.NAPTR, '100 10 "u!" "s" "" .', "flags must be letters or digits"),
    (RecordType.NAPTR, '100 10 "u" "s" "" "quoted."', "not a valid domain name"),
    (RecordType.NAPTR, '100 10 "u" "s" "open .', "Quotation marks are not balanced"),
    (RecordType.NAPTR, f'100 10 "u" "{"s" * 256}" "" .', "longer than 255"),
    (RecordType.DS, "12345 13 2", "doesn't have 4 fields"),
    (RecordType.DS, f"70000 13 2 {SHA256}", "key tag must be between 0 and 65535"),
    (RecordType.DS, f"1 300 2 {SHA256}", "algorithm must be between 0 and 255"),
    (RecordType.DS, f"1 13 3 {SHA256}", "digest type must be 1, 2 or 4"),
    (RecordType.DS, f"1 13 2 {SHA1}", "must be 64 hexadecimal digits"),
    (RecordType.DS, f"1 13 1 {SHA256}", "must be 40 hexadecimal digits"),
    (RecordType.DS, f"1 13 2 {'zz' * 32}", "must be 64 hexadecimal digits"),
    (RecordType.TLSA, f"3 1 {SHA256}", "doesn't have 4 fields"),
    (RecordType.TLSA, f"4 1 1 {SHA256}", "certificate usage must be 0 to 3"),
    (RecordType.TLSA, f"3 2 1 {SHA256}", "selector must be 0 or 1"),
    (RecordType.TLSA, f"3 1 3 {SHA256}", "matching type must be 0, 1 or 2"),
    (RecordType.TLSA, f"3 1 1 {SHA1}", "must be 64 hexadecimal digits"),
    (RecordType.TLSA, f"3 1 2 {SHA256}", "must be 128 hexadecimal digits"),
    (RecordType.TLSA, "3 1 0 abc", "an even number of hexadecimal digits"),
    (RecordType.SSHFP, f"1 {SHA1}", "doesn't have 3 fields"),
    (RecordType.SSHFP, f"5 1 {SHA1}", "algorithm must be 1, 2, 3, 4 or 6"),
    (RecordType.SSHFP, f"1 3 {SHA1}", "fingerprint type must be 1 or 2"),
    (RecordType.SSHFP, f"1 1 {SHA256}", "must be 40 hexadecimal digits"),
    (RecordType.SSHFP, f"1 2 {SHA1}", "must be 64 hexadecimal digits"),
    (RecordType.HTTPS, "1", "needs a priority and a target"),
    (RecordType.HTTPS, "x .", "Priority must be between 0 and 65535"),
    (RecordType.HTTPS, "70000 .", "Priority must be between 0 and 65535"),
    (RecordType.HTTPS, "0 . alpn=h2", "is an alias and takes no parameters"),
    (RecordType.HTTPS, "1 . alpn=h2 alpn=h3", "'alpn' is given twice"),
    (RecordType.HTTPS, "1 . alpn=", "Parameters must be key or key=value"),
    (RecordType.HTTPS, "1 . alpn", "alpn must be a comma-separated list"),
    (RecordType.HTTPS, "1 . port=99999", "port must be between 0 and 65535"),
    (RecordType.HTTPS, "1 . ipv4hint=1.2.3", "list of IPv4 addresses"),
    (RecordType.HTTPS, "1 . ipv6hint=192.0.2.1", "list of IPv6 addresses"),
    (RecordType.HTTPS, "1 . no-default-alpn=1", "no-default-alpn takes no value"),
    (RecordType.HTTPS, "1 . ech=not*base64", "ech must be base64"),
    (RecordType.HTTPS, "1 . bogus=1", "'bogus' is not a service parameter"),
    (RecordType.HTTPS, '1 . "alpn=h2"', "Parameters must be key or key=value"),
    (RecordType.HTTPS, '1 . alpn="h2', "Parameters must be key or key=value"),
    (RecordType.SVCB, "1 . key70000=x", "'key70000' is not a service parameter"),
]


@pytest.mark.parametrize(("record_type", "value"), VALID)
def test_valid_values_are_accepted_unchanged(record_type: RecordType, value: str) -> None:
    assert validate_values(record_type, [f"  {value}  "]) == [value]


@pytest.mark.parametrize(("record_type", "value", "message"), INVALID)
def test_invalid_values_are_rejected(record_type: RecordType, value: str, message: str) -> None:
    with pytest.raises(RecordValueError, match=message.replace("(", r"\(")) as error:
        validate_values(record_type, [value])
    assert str(error.value).startswith("Invalid Resource Record: 'FATAL problem: ")


@pytest.mark.parametrize("record_type", sorted(EXAMPLES))
def test_records_are_stored_listed_edited_and_deleted(
    client: TestClient, zone: dict[str, Any], record_type: str
) -> None:
    name, values = EXAMPLES[record_type]
    base = f"{API}/hostedzones/{zone['id']}/records"
    created = create_record(client, zone["id"], name, record_type, values)
    assert created["type"] == record_type
    assert created["values"] == values

    assert client.get(f"{base}/{created['id']}").json() == created
    listed = client.get(base, params={"type": record_type}).json()
    assert [record["id"] for record in listed["items"]] == [created["id"]]
    found = client.get(base, params={"filter": f"type:eq:{record_type}"}).json()
    assert found["total"] == 1

    edited = client.patch(f"{base}/{created['id']}", json={"ttl": 86400, "values": values[:1]})
    assert edited.status_code == 200, edited.text
    assert (edited.json()["ttl"], edited.json()["values"]) == (86400, values[:1])

    assert client.delete(f"{base}/{created['id']}").status_code == 204
    assert client.get(base, params={"type": record_type}).json()["total"] == 0


def test_an_invalid_value_is_refused_by_the_api_with_route_53s_wording(
    client: TestClient, zone: dict[str, Any]
) -> None:
    response = client.post(
        f"{API}/hostedzones/{zone['id']}/records",
        json={"name": "child", "type": "DS", "ttl": 300, "values": ["12345 13 2 abcd"]},
    )
    assert response.status_code == 400
    assert response.json()["message"] == (
        "Invalid Resource Record: 'FATAL problem: DSRRDATAIllegalDigest (DS digest must be "
        "64 hexadecimal digits for digest type 2) encountered with '12345 13 2 abcd''"
    )


def test_a_ds_record_belongs_to_a_delegation_not_to_the_apex(
    client: TestClient, zone: dict[str, Any]
) -> None:
    response = client.post(
        f"{API}/hostedzones/{zone['id']}/records",
        json={"name": "", "type": "DS", "ttl": 300, "values": [f"12345 13 2 {SHA256}"]},
    )
    assert response.status_code == 400
    assert "DS with DNS name example.com. is not permitted at apex" in response.json()["message"]


def test_a_cname_still_excludes_every_other_type_at_its_name(
    client: TestClient, zone: dict[str, Any]
) -> None:
    create_record(client, zone["id"], "www", "CNAME", ["target.example.net"])
    for record_type, (_, values) in EXAMPLES.items():
        response = client.post(
            f"{API}/hostedzones/{zone['id']}/records",
            json={"name": "www", "type": record_type, "ttl": 300, "values": values},
        )
        assert response.status_code in (400, 409), record_type
        assert "CNAME" in response.json()["message"], record_type


def test_the_new_types_can_be_weighted_like_any_other(
    client: TestClient, zone: dict[str, Any]
) -> None:
    for identifier, weight in (("a", 10), ("b", 90)):
        record = create_record(
            client,
            zone["id"],
            "svc",
            "HTTPS",
            ["1 . alpn=h2"],
            routing_policy="weighted",
            set_identifier=identifier,
            weight=weight,
        )
        assert (record["routing_policy"], record["weight"]) == ("weighted", weight)


ZONE_FILE = f"""$ORIGIN example.com.
$TTL 300
@              IN SPF   "v=spf1 ip4:192.0.2.0/24 -all"
@              IN HTTPS 1 . alpn="h3,h2" ipv4hint="192.0.2.1,192.0.2.2"
_dns           IN SVCB  1 doh alpn=h2 port=443
_dns           IN SVCB  0 pool.example.net.
sip            IN NAPTR 100 10 "u" "sip+E2U" "!^.*$!sip:info@example.com!i" .
sip            IN NAPTR 110 10 "S" "SIP+D2U" "" _sip._udp
child          IN DS    12345 13 2 ( {SHA256[:32]}
                                     {SHA256[32:]} )
_443._tcp.www  IN TLSA  3 1 1 {SHA256}
host           IN SSHFP 4 2 {SHA256[:40]} {SHA256[40:]}
host           IN SSHFP 1 1 {SHA1}
"""

PARSED = {
    ("example.com.", "SPF"): ['"v=spf1 ip4:192.0.2.0/24 -all"'],
    ("example.com.", "HTTPS"): ['1 . alpn="h3,h2" ipv4hint="192.0.2.1,192.0.2.2"'],
    ("_dns.example.com.", "SVCB"): [
        "1 doh.example.com. alpn=h2 port=443",
        "0 pool.example.net.",
    ],
    ("sip.example.com.", "NAPTR"): [
        '100 10 "u" "sip+E2U" "!^.*$!sip:info@example.com!i" .',
        '110 10 "S" "SIP+D2U" "" _sip._udp.example.com.',
    ],
    ("child.example.com.", "DS"): [f"12345 13 2 {SHA256}"],
    ("_443._tcp.www.example.com.", "TLSA"): [f"3 1 1 {SHA256}"],
    ("host.example.com.", "SSHFP"): [f"4 2 {SHA256}", f"1 1 {SHA1}"],
}


def test_zone_files_with_the_new_types_are_parsed() -> None:
    parsed = parse_zone_file(ZONE_FILE, "example.com.")
    assert parsed.issues == []
    assert {
        (record.name, record.type.value): record.values for record in parsed.record_sets
    } == PARSED


@pytest.mark.parametrize(
    ("line", "message"),
    [
        ("x IN NAPTR 100 10 u s\n", "NAPTR record data must have 6 fields"),
        ("x IN DS 12345 13 2\n", "DS record data must have 4 fields"),
        ("x IN TLSA 3 1\n", "TLSA record data must have 4 fields"),
        ("x IN SSHFP 1\n", "SSHFP record data must have 3 fields"),
        ("x IN HTTPS 1\n", "HTTPS record data needs a priority and a target"),
        ("x IN DS 12345 13 2 abcd\n", "must be 64 hexadecimal digits"),
        ("x IN SVCB 1 . bogus=1\n", "'bogus' is not a service parameter"),
    ],
)
def test_zone_file_problems_in_the_new_types_are_reported(line: str, message: str) -> None:
    parsed = parse_zone_file(f"$TTL 300\n{line}", "example.com.")
    assert [issue.line for issue in parsed.issues] == [2]
    assert message in parsed.issues[0].message


def _records(client: TestClient, zone_id: str) -> dict[tuple[str, str], list[str]]:
    items = client.get(f"{API}/hostedzones/{zone_id}/records?page_size=500").json()["items"]
    return {
        (record["name"], record["type"]): record["values"]
        for record in items
        if record["type"] not in ("NS", "SOA")
    }


def test_import_then_export_then_import_again_gives_the_same_records(client: TestClient) -> None:
    first = create_zone(client, "example.com")["id"]
    imported = client.post(
        f"{API}/hostedzones/{first}/import", json={"content": ZONE_FILE, "dry_run": False}
    )
    assert imported.status_code == 200, imported.text
    assert imported.json()["summary"] == {"create": 7, "replace": 0, "skip": 0, "error": 0}
    assert _records(client, first) == PARSED

    exported = client.get(f"{API}/hostedzones/{first}/export?format=bind").text
    second = create_zone(client, "example.com")["id"]
    again = client.post(
        f"{API}/hostedzones/{second}/import", json={"content": exported, "dry_run": False}
    )
    assert again.status_code == 200, again.text
    assert _records(client, second) == PARSED

    document = client.get(f"{API}/hostedzones/{first}/export?format=json").json()
    by_key = {(entry["Name"], entry["Type"]): entry for entry in document["ResourceRecordSets"]}
    for key, values in PARSED.items():
        assert [record["Value"] for record in by_key[key]["ResourceRecords"]] == values
