from typing import Any

import pytest
from fastapi.testclient import TestClient

from tests.conftest import API, create_record, create_zone
from tests.test_records_api import ONE_OF_EACH

ZONE_FILE = """\
$ORIGIN example.com.
$TTL 3600
@       IN SOA ns1.example.com. hostmaster.example.com. 1 7200 900 1209600 86400
@       IN NS  ns1.example.com.
@       IN A   192.0.2.10
www     IN A   192.0.2.10
www     IN A   192.0.2.11
blog 60 IN CNAME www
@       IN MX  10 mail
@       IN TXT "v=spf1 ~all"
"""


def _url(zone: dict[str, Any], suffix: str) -> str:
    return f"{API}/hostedzones/{zone['id']}/{suffix}"


def _import(client: TestClient, zone: dict[str, Any], content: str, **options: Any) -> Any:
    return client.post(_url(zone, "import"), json={"content": content, **options})


def _records(
    client: TestClient, zone: dict[str, Any]
) -> set[tuple[str, str, int, tuple[str, ...]]]:
    items = client.get(_url(zone, "records"), params={"page_size": 500}).json()["items"]
    return {(item["name"], item["type"], item["ttl"], tuple(item["values"])) for item in items}


@pytest.fixture
def populated(client: TestClient, zone: dict[str, Any]) -> dict[str, Any]:
    for name, record_type, values in ONE_OF_EACH:
        create_record(client, zone["id"], name, record_type, values)
    return zone


def test_preview_is_the_default_and_saves_nothing(client: TestClient, zone: dict[str, Any]) -> None:
    before = _records(client, zone)
    response = _import(client, zone, ZONE_FILE)
    assert response.status_code == 200, response.text
    body = response.json()

    assert (body["dry_run"], body["applied"]) == (True, False)
    assert body["summary"] == {"create": 5, "replace": 0, "skip": 2, "error": 0}
    assert body["errors"] == []
    statuses = {(entry["name"], entry["type"]): entry["status"] for entry in body["record_sets"]}
    assert statuses == {
        ("example.com.", "SOA"): "skip",
        ("example.com.", "NS"): "skip",
        ("example.com.", "A"): "create",
        ("www.example.com.", "A"): "create",
        ("blog.example.com.", "CNAME"): "create",
        ("example.com.", "MX"): "create",
        ("example.com.", "TXT"): "create",
    }
    skipped = body["record_sets"][0]
    assert skipped["line"] == 3
    assert "Route 53 manages the SOA record" in skipped["reason"]
    assert _records(client, zone) == before


def test_import_creates_the_records_and_keeps_the_zones_own_apex(
    client: TestClient, zone: dict[str, Any]
) -> None:
    apex = _records(client, zone)
    response = _import(client, zone, ZONE_FILE, dry_run=False)
    assert response.status_code == 200, response.text
    assert response.json()["applied"] is True

    assert _records(client, zone) == apex | {
        ("example.com.", "A", 3600, ("192.0.2.10",)),
        ("www.example.com.", "A", 3600, ("192.0.2.10", "192.0.2.11")),
        ("blog.example.com.", "CNAME", 60, ("www.example.com.",)),
        ("example.com.", "MX", 3600, ("10 mail.example.com.",)),
        ("example.com.", "TXT", 3600, ('"v=spf1 ~all"',)),
    }


def test_existing_records_block_an_import_unless_replaced(
    client: TestClient, zone: dict[str, Any]
) -> None:
    create_record(client, zone["id"], "www", "A", ["198.51.100.1"])
    before = _records(client, zone)

    preview = _import(client, zone, ZONE_FILE).json()
    assert preview["summary"] == {"create": 4, "replace": 0, "skip": 2, "error": 1}
    failed = next(entry for entry in preview["record_sets"] if entry["status"] == "error")
    assert failed["reason"] == (
        "Tried to create resource record set [name='www.example.com.', type='A'] "
        "but it already exists"
    )

    blocked = _import(client, zone, ZONE_FILE, dry_run=False)
    assert blocked.status_code == 400
    assert blocked.json()["code"] == "InvalidZoneFile"
    assert blocked.json()["details"] == [{"line": 6, "message": failed["reason"]}]
    assert _records(client, zone) == before

    replaced = _import(client, zone, ZONE_FILE, dry_run=False, replace_existing=True)
    assert replaced.status_code == 200
    assert replaced.json()["summary"] == {"create": 4, "replace": 1, "skip": 2, "error": 0}
    assert ("www.example.com.", "A", 3600, ("192.0.2.10", "192.0.2.11")) in _records(client, zone)


def test_syntax_errors_are_listed_by_line_and_block_the_import(
    client: TestClient, zone: dict[str, Any]
) -> None:
    content = "good 300 IN A 192.0.2.1\nbad 300 IN A 999.1.1.1\nodd 300 IN HINFO a b\n"
    before = _records(client, zone)

    preview = _import(client, zone, content).json()
    assert preview["summary"] == {"create": 1, "replace": 0, "skip": 0, "error": 0}
    assert [error["line"] for error in preview["errors"]] == [2, 3]
    assert "valid IPv4 address" in preview["errors"][0]["message"]
    assert preview["errors"][1]["message"] == "Record type HINFO is not supported"

    blocked = _import(client, zone, content, dry_run=False)
    assert blocked.status_code == 400
    assert [detail["line"] for detail in blocked.json()["details"]] == [2, 3]
    assert _records(client, zone) == before


def test_rule_violations_show_up_in_the_preview(client: TestClient, zone: dict[str, Any]) -> None:
    content = "www 300 IN A 192.0.2.1\nwww 300 IN CNAME other.example.com.\n"
    preview = _import(client, zone, content).json()
    assert preview["summary"]["error"] == 1
    failed = next(entry for entry in preview["record_sets"] if entry["status"] == "error")
    assert (failed["type"], failed["line"]) == ("CNAME", 2)
    assert "conflicts with other records" in failed["reason"]


def test_a_file_with_nothing_to_import_is_rejected(
    client: TestClient, zone: dict[str, Any]
) -> None:
    only_apex = "@ 300 IN NS ns1.example.com.\n"
    assert _import(client, zone, only_apex).json()["summary"]["skip"] == 1

    response = _import(client, zone, only_apex, dry_run=False)
    assert response.status_code == 400
    assert response.json()["message"] == "The zone file does not contain any records to import."
    assert _import(client, zone, "").status_code == 422


def test_bind_export_is_a_downloadable_zone_file(
    client: TestClient, populated: dict[str, Any]
) -> None:
    response = client.get(_url(populated, "export"))
    assert response.status_code == 200
    assert response.headers["content-type"].startswith("text/plain")
    assert response.headers["content-disposition"] == 'attachment; filename="example.com.zone"'

    lines = response.text.splitlines()
    assert lines[0] == f"; Zone file for example.com. (hosted zone {populated['id']})"
    assert "$ORIGIN example.com." in lines
    assert "www.example.com.\t300\tIN\tA\t192.0.2.10" in lines
    assert "blog.example.com.\t300\tIN\tCNAME\twww.example.com." in lines
    assert "example.com.\t300\tIN\tMX\t10 mail.example.com." in lines
    assert 'example.com.\t300\tIN\tCAA\t0 issue "amazon.com"' in lines
    assert any(line.startswith("example.com.\t900\tIN\tSOA\t") for line in lines)


def test_bind_export_round_trips_through_import(
    client: TestClient, populated: dict[str, Any]
) -> None:
    exported = client.get(_url(populated, "export"), params={"format": "bind"}).text
    target = create_zone(client, "example.com")

    response = _import(client, target, exported, dry_run=False)
    assert response.status_code == 200, response.text
    assert response.json()["summary"] == {"create": 9, "replace": 0, "skip": 2, "error": 0}

    def without_apex(records: set[tuple[str, str, int, tuple[str, ...]]]) -> set[Any]:
        return {
            record
            for record in records
            if not (record[0] == "example.com." and record[1] in ("NS", "SOA"))
        }

    reexported = client.get(_url(target, "export")).text
    original = without_apex(_records(client, populated))
    imported = without_apex(_records(client, target))
    assert len(imported) == len(original) == 9
    # Host names come back fully qualified, so compare the canonical zone files.
    assert [
        line
        for line in reexported.splitlines()[2:]
        if "\tNS\tns-" not in line and "SOA" not in line
    ] == [
        line for line in exported.splitlines()[2:] if "\tNS\tns-" not in line and "SOA" not in line
    ]


def test_records_a_zone_file_cannot_express_are_listed_as_comments(
    client: TestClient, zone: dict[str, Any]
) -> None:
    client.post(
        _url(zone, "records"),
        json={
            "name": "cdn",
            "type": "A",
            "alias_target": {"dns_name": "d1.cloudfront.net", "hosted_zone_id": "Z2FDTNDATAQYW2"},
        },
    )
    text = client.get(_url(zone, "export")).text
    assert "; Not exported (alias or routing policy record): cdn.example.com. A" in text
    assert "cdn.example.com.\t" not in text


def test_json_export_uses_the_aws_cli_shape(client: TestClient, zone: dict[str, Any]) -> None:
    create_record(client, zone["id"], "www", "A", ["192.0.2.1", "192.0.2.2"])
    client.post(
        _url(zone, "records"),
        json={
            "name": "lb",
            "type": "A",
            "ttl": 60,
            "values": ["192.0.2.3"],
            "routing_policy": "weighted",
            "set_identifier": "blue",
            "weight": 10,
        },
    )
    client.post(
        _url(zone, "records"),
        json={
            "name": "cdn",
            "type": "A",
            "alias_target": {"dns_name": "d1.cloudfront.net", "hosted_zone_id": "Z2FDTNDATAQYW2"},
        },
    )
    client.put(_url(zone, "tags"), json={"tags": [{"key": "env", "value": "demo"}]})

    response = client.get(_url(zone, "export"), params={"format": "json"})
    assert response.status_code == 200
    assert response.headers["content-type"] == "application/json"
    assert response.headers["content-disposition"] == 'attachment; filename="example.com.json"'

    document = response.json()
    assert document["HostedZone"] == {
        "Id": f"/hostedzone/{zone['id']}",
        "Name": "example.com.",
        "CallerReference": zone["caller_reference"],
        "Config": {"Comment": "", "PrivateZone": False},
        "ResourceRecordSetCount": 5,
    }
    assert document["DelegationSet"]["NameServers"] == [
        name.removesuffix(".") for name in zone["name_servers"]
    ]
    assert document["Tags"] == [{"Key": "env", "Value": "demo"}]

    record_sets = {(item["Name"], item["Type"]): item for item in document["ResourceRecordSets"]}
    assert record_sets[("www.example.com.", "A")] == {
        "Name": "www.example.com.",
        "Type": "A",
        "TTL": 300,
        "ResourceRecords": [{"Value": "192.0.2.1"}, {"Value": "192.0.2.2"}],
    }
    assert record_sets[("lb.example.com.", "A")] == {
        "Name": "lb.example.com.",
        "Type": "A",
        "SetIdentifier": "blue",
        "Weight": 10,
        "TTL": 60,
        "ResourceRecords": [{"Value": "192.0.2.3"}],
    }
    assert record_sets[("cdn.example.com.", "A")] == {
        "Name": "cdn.example.com.",
        "Type": "A",
        "AliasTarget": {
            "HostedZoneId": "Z2FDTNDATAQYW2",
            "DNSName": "d1.cloudfront.net.",
            "EvaluateTargetHealth": False,
        },
    }


def test_private_zone_json_export_lists_vpcs(client: TestClient) -> None:
    vpc = {"vpc_id": "vpc-0a1b2c3d4e5f67890", "region": "us-east-1"}
    zone = create_zone(client, "corp.internal", type="private", vpcs=[vpc])
    document = client.get(_url(zone, "export"), params={"format": "json"}).json()
    assert document["HostedZone"]["Config"]["PrivateZone"] is True
    assert document["VPCs"] == [{"VPCRegion": "us-east-1", "VPCId": "vpc-0a1b2c3d4e5f67890"}]
    assert "DelegationSet" not in document


def test_export_and_import_require_a_known_zone_and_format(
    client: TestClient, zone: dict[str, Any]
) -> None:
    assert client.get(f"{API}/hostedzones/Z404/export").status_code == 404
    assert client.post(f"{API}/hostedzones/Z404/import", json={"content": "x"}).status_code == 404
    assert client.get(_url(zone, "export"), params={"format": "yaml"}).status_code == 422


def test_export_file_names_are_safe_for_any_zone_name(client: TestClient) -> None:
    zone = create_zone(client, 'we"ird/na;me.example.com')
    response = client.get(f"{API}/hostedzones/{zone['id']}/export", params={"format": "json"})
    assert response.status_code == 200
    assert (
        response.headers["content-disposition"]
        == 'attachment; filename="we_ird_na_me.example.com.json"'
    )
