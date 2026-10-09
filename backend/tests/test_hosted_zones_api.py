import re
from typing import Any

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models import HostedZone, RecordSet, RecordValue, User
from app.services.auth import hash_password
from tests.conftest import API, create_record, create_zone

ZONES = f"{API}/hostedzones"
VPC = {"vpc_id": "vpc-0a1b2c3d4e5f67890", "region": "us-east-1"}


def _records(client: TestClient, zone_id: str) -> list[dict[str, Any]]:
    items: list[dict[str, Any]] = client.get(f"{ZONES}/{zone_id}/records").json()["items"]
    return items


def _names(client: TestClient, **params: Any) -> list[str]:
    response = client.get(ZONES, params=params)
    assert response.status_code == 200, response.text
    return [zone["name"] for zone in response.json()["items"]]


def test_create_returns_a_route53_style_zone(client: TestClient) -> None:
    zone = create_zone(client, "Example.COM", description="  Demo zone  ")
    assert re.fullmatch(r"Z[A-Z0-9]{20}", zone["id"])
    assert zone["name"] == "example.com."
    assert zone["type"] == "public"
    assert zone["description"] == "Demo zone"
    assert zone["created_by"] == "Route 53"
    assert zone["record_count"] == 2
    assert zone["vpcs"] == []
    assert zone["tags"] == []
    assert len(zone["name_servers"]) == 4


def test_create_adds_the_apex_ns_and_soa_records(client: TestClient) -> None:
    zone = create_zone(client)
    ns, soa = _records(client, zone["id"])

    assert (ns["name"], ns["type"], ns["ttl"]) == ("example.com.", "NS", 172800)
    assert ns["values"] == zone["name_servers"]
    patterns = [
        r"ns-(\d+)\.awsdns-\d{2}\.co\.uk\.",
        r"ns-(\d+)\.awsdns-\d{2}\.com\.",
        r"ns-(\d+)\.awsdns-\d{2}\.org\.",
        r"ns-(\d+)\.awsdns-\d{2}\.net\.",
    ]
    for value, pattern in zip(ns["values"], patterns, strict=True):
        assert re.fullmatch(pattern, value), value

    assert (soa["name"], soa["type"], soa["ttl"]) == ("example.com.", "SOA", 900)
    assert soa["values"] == [
        f"{ns['values'][0]} awsdns-hostmaster.amazon.com. 1 7200 900 1209600 86400"
    ]


def test_duplicate_names_are_allowed_with_distinct_ids(client: TestClient) -> None:
    first, second = create_zone(client), create_zone(client)
    assert first["name"] == second["name"]
    assert first["id"] != second["id"]
    assert first["name_servers"] != second["name_servers"]


@pytest.mark.parametrize("name", ["bad..name", "münchen.de", "has space.com", "*.example.com", "."])
def test_invalid_domain_names_are_rejected(client: TestClient, name: str) -> None:
    response = client.post(ZONES, json={"name": name})
    assert response.status_code == 400
    body = response.json()
    assert body["code"] == "InvalidDomainName"
    assert body["details"] == [{"field": "name", "message": body["message"]}]


def test_invalid_domain_name_uses_route53_wording(client: TestClient) -> None:
    response = client.post(ZONES, json={"name": "bad..name"})
    assert response.json()["message"] == (
        "DomainLabelEmpty (Domain label is empty) encountered with 'bad..name'"
    )


@pytest.mark.parametrize("name", ["my!zone.com", "a&b.com", "-lead.com"])
def test_names_may_use_the_characters_the_console_lists(client: TestClient, name: str) -> None:
    assert create_zone(client, name)["name"] == f"{name}."


def test_empty_name_fails_request_validation(client: TestClient) -> None:
    response = client.post(ZONES, json={"name": ""})
    assert response.status_code == 422
    assert response.json()["details"][0]["field"] == "name"


def test_private_zone_keeps_its_vpcs_and_fixed_name_servers(client: TestClient) -> None:
    zone = create_zone(client, "corp.internal", type="private", vpcs=[VPC])
    assert zone["type"] == "private"
    assert zone["vpcs"] == [VPC]
    assert zone["name_servers"] == [
        "ns-1536.awsdns-00.co.uk.",
        "ns-0.awsdns-00.com.",
        "ns-1024.awsdns-00.org.",
        "ns-512.awsdns-00.net.",
    ]


@pytest.mark.parametrize(
    ("payload", "message"),
    [
        ({"type": "private"}, "must be associated with at least one VPC"),
        ({"type": "private", "vpcs": [{"vpc_id": "vpc-xyz", "region": "us-east-1"}]}, "VPC ID"),
        ({"type": "private", "vpcs": [VPC | {"region": "mars-1"}]}, "Region 'mars-1'"),
        ({"type": "private", "vpcs": [VPC, VPC]}, "more than once"),
        ({"type": "public", "vpcs": [VPC]}, "only be associated with private"),
    ],
)
def test_vpc_rules(client: TestClient, payload: dict[str, Any], message: str) -> None:
    response = client.post(ZONES, json={"name": "corp.internal", **payload})
    assert response.status_code == 400
    assert message in response.json()["message"]
    assert response.json()["details"][0]["field"] == "vpcs"


def test_get_returns_the_zone_with_a_live_record_count(client: TestClient) -> None:
    zone = create_zone(client, tags=[{"key": "env", "value": "demo"}])
    create_record(client, zone["id"], "www", "A", ["192.0.2.1"])

    response = client.get(f"{ZONES}/{zone['id']}")
    assert response.status_code == 200
    body = response.json()
    assert body["record_count"] == 3
    assert body["tags"] == [{"key": "env", "value": "demo"}]
    assert body["name_servers"] == zone["name_servers"]


def test_unknown_zone_is_a_404_in_route53_wording(client: TestClient) -> None:
    for method in ("get", "delete"):
        response = getattr(client, method)(f"{ZONES}/Z404")
        assert response.status_code == 404
        assert response.json() == {
            "code": "NoSuchHostedZone",
            "message": "No hosted zone found with ID: Z404",
            "details": [],
        }


def test_zones_of_another_user_are_invisible(client: TestClient, db: Session) -> None:
    other = User(
        email="other@example.com",
        password_hash=hash_password("irrelevant"),
        display_name="other",
        account_id="999988887777",
    )
    db.add(other)
    db.flush()
    db.add(
        HostedZone(
            id="ZOTHERUSER0000000000A",
            owner_id=other.id,
            name="private-to-other.com.",
            sort_key="com.private-to-other",
            type="public",
            caller_reference="other-ref",
        )
    )
    db.commit()

    assert _names(client) == []
    assert client.get(f"{ZONES}/ZOTHERUSER0000000000A").status_code == 404
    assert client.delete(f"{ZONES}/ZOTHERUSER0000000000A").status_code == 404


def test_only_the_description_can_be_edited(client: TestClient, zone: dict[str, Any]) -> None:
    response = client.patch(
        f"{ZONES}/{zone['id']}", json={"description": "Updated", "name": "other.com"}
    )
    assert response.status_code == 200
    body = response.json()
    assert body["description"] == "Updated"
    assert body["name"] == "example.com."
    assert body["updated_at"] >= zone["updated_at"]
    assert client.get(f"{ZONES}/{zone['id']}").json()["description"] == "Updated"


def test_description_is_limited_to_256_characters(client: TestClient, zone: dict[str, Any]) -> None:
    response = client.patch(f"{ZONES}/{zone['id']}", json={"description": "x" * 257})
    assert response.status_code == 422


def test_delete_removes_the_zone_and_its_records(
    client: TestClient, zone: dict[str, Any], db: Session
) -> None:
    assert client.delete(f"{ZONES}/{zone['id']}").status_code == 204
    assert client.get(f"{ZONES}/{zone['id']}").status_code == 404
    assert db.scalar(select(func.count(RecordSet.id))) == 0
    assert db.scalar(select(func.count()).select_from(RecordValue)) == 0


def test_delete_is_blocked_while_the_zone_has_other_records(
    client: TestClient, zone: dict[str, Any]
) -> None:
    record = create_record(client, zone["id"], "www", "A", ["192.0.2.1"])

    response = client.delete(f"{ZONES}/{zone['id']}")
    assert response.status_code == 409
    assert response.json() == {
        "code": "HostedZoneNotEmpty",
        "message": "The specified hosted zone contains non-required resource record sets "
        "and so cannot be deleted.",
        "details": [],
    }

    client.delete(f"{ZONES}/{zone['id']}/records/{record['id']}")
    assert client.delete(f"{ZONES}/{zone['id']}").status_code == 204


def test_an_extra_apex_ns_free_record_still_blocks_deletion(
    client: TestClient, zone: dict[str, Any]
) -> None:
    create_record(client, zone["id"], "", "TXT", ['"apex"'])
    assert client.delete(f"{ZONES}/{zone['id']}").status_code == 409


@pytest.fixture
def several_zones(client: TestClient) -> list[dict[str, Any]]:
    zones = [
        create_zone(client, "alpha.com", description="First"),
        create_zone(client, "beta-shop.net", description="Storefront"),
        create_zone(client, "gamma.internal", type="private", vpcs=[VPC]),
        create_zone(client, "delta.org", description="shop backend"),
    ]
    create_record(client, zones[1]["id"], "www", "A", ["192.0.2.1"])
    create_record(client, zones[1]["id"], "api", "A", ["192.0.2.2"])
    return zones


def test_list_is_sorted_by_domain_by_default(
    client: TestClient, several_zones: list[dict[str, Any]]
) -> None:
    body = client.get(ZONES).json()
    # Ordered by domain from the right, as Route 53 lists them: com, internal, net, org.
    assert [zone["name"] for zone in body["items"]] == [
        "alpha.com.",
        "gamma.internal.",
        "beta-shop.net.",
        "delta.org.",
    ]
    assert (body["total"], body["page"], body["page_size"], body["pages"]) == (4, 1, 50, 1)
    assert "name_servers" not in body["items"][0]


@pytest.mark.parametrize(
    ("params", "expected"),
    [
        ({"search": "SHOP"}, ["beta-shop.net.", "delta.org."]),
        ({"search": "internal"}, ["gamma.internal."]),
        ({"search": "nothing-matches"}, []),
        ({"search": "100%"}, []),
        ({"type": "private"}, ["gamma.internal."]),
        ({"type": "public", "search": "shop"}, ["beta-shop.net.", "delta.org."]),
        ({"filter": "name:eq:alpha.com"}, ["alpha.com."]),
        ({"filter": "name:eq:ALPHA.com."}, ["alpha.com."]),
        ({"filter": "name:ne:alpha.com"}, ["beta-shop.net.", "delta.org.", "gamma.internal."]),
        ({"filter": "name:contains:a."}, ["alpha.com.", "delta.org.", "gamma.internal."]),
        ({"filter": "name:starts_with:be"}, ["beta-shop.net."]),
        (
            {"filter": "description:not_contains:shop"},
            ["alpha.com.", "beta-shop.net.", "gamma.internal."],
        ),
        ({"filter": "type:eq:Private"}, ["gamma.internal."]),
        ({"filter": "record_count:gt:2"}, ["beta-shop.net."]),
        ({"filter": "record_count:eq:2"}, ["alpha.com.", "delta.org.", "gamma.internal."]),
        ({"filter": "any:contains:SHOP"}, ["beta-shop.net.", "delta.org."]),
        ({"filter": ["any:contains:shop", "any:contains:beta"]}, ["beta-shop.net."]),
        ({"filter": "any:not_contains:shop"}, ["alpha.com.", "gamma.internal."]),
        ({"filter": ["type:eq:public", "description:contains:shop"]}, ["delta.org."]),
        (
            {"filter": ["name:starts_with:alpha", "name:starts_with:gamma"], "filter_mode": "or"},
            ["alpha.com.", "gamma.internal."],
        ),
    ],
)
def test_search_and_filters(
    client: TestClient,
    several_zones: list[dict[str, Any]],
    params: dict[str, Any],
    expected: list[str],
) -> None:
    assert sorted(_names(client, **params)) == sorted(expected)


def test_filter_by_id(client: TestClient, several_zones: list[dict[str, Any]]) -> None:
    target = several_zones[2]
    assert _names(client, filter=f"id:eq:{target['id']}") == [target["name"]]
    assert _names(client, search=target["id"][:12]) == [target["name"]]


@pytest.mark.parametrize(
    ("params", "expected"),
    [
        ({"sort": "name", "order": "desc"}, ["delta", "beta-shop", "gamma", "alpha"]),
        ({"sort": "record_count", "order": "desc"}, ["beta-shop", "alpha", "gamma", "delta"]),
        ({"sort": "type"}, ["gamma", "alpha", "beta-shop", "delta"]),
        ({"sort": "description"}, ["gamma", "alpha", "delta", "beta-shop"]),
        ({"sort": "created_at", "order": "desc"}, ["delta", "gamma", "beta-shop", "alpha"]),
    ],
)
def test_sorting(
    client: TestClient,
    several_zones: list[dict[str, Any]],
    params: dict[str, Any],
    expected: list[str],
) -> None:
    assert [name.split(".")[0] for name in _names(client, **params)] == expected


def test_pagination(client: TestClient, several_zones: list[dict[str, Any]]) -> None:
    first = client.get(ZONES, params={"page_size": 3}).json()
    second = client.get(ZONES, params={"page_size": 3, "page": 2}).json()
    beyond = client.get(ZONES, params={"page_size": 3, "page": 9}).json()

    assert [zone["name"] for zone in first["items"]] == [
        "alpha.com.",
        "gamma.internal.",
        "beta-shop.net.",
    ]
    assert [zone["name"] for zone in second["items"]] == ["delta.org."]
    assert (first["total"], first["pages"]) == (4, 2)
    assert (beyond["items"], beyond["total"], beyond["pages"]) == ([], 4, 2)


@pytest.mark.parametrize(
    ("params", "status", "message"),
    [
        ({"filter": "name"}, 400, "must have the form field:operator:value"),
        ({"filter": "name:like:x"}, 400, "operator 'like' is not supported"),
        ({"filter": "colour:eq:red"}, 400, "Cannot filter by 'colour'"),
        ({"filter": "record_count:gt:many"}, 400, "must be a whole number"),
        ({"filter": "name:gt:a"}, 400, "cannot be used on a text property"),
        ({"filter": "any:eq:a"}, 400, "Free-text filters support only contains"),
        ({"sort": "colour"}, 400, "Cannot sort by 'colour'"),
        ({"page": 0}, 422, "The request is not valid."),
        ({"page_size": 501}, 422, "The request is not valid."),
        ({"order": "sideways"}, 422, "The request is not valid."),
        ({"type": "hybrid"}, 422, "The request is not valid."),
    ],
)
def test_bad_list_parameters(
    client: TestClient, params: dict[str, Any], status: int, message: str
) -> None:
    response = client.get(ZONES, params=params)
    assert response.status_code == status
    assert message in response.json()["message"]


def test_tags_can_be_replaced(client: TestClient, zone: dict[str, Any]) -> None:
    url = f"{ZONES}/{zone['id']}/tags"
    assert client.get(url).json() == {"tags": []}

    first = client.put(
        url, json={"tags": [{"key": "env", "value": "demo"}, {"key": "owner", "value": "me"}]}
    )
    assert first.status_code == 200
    assert first.json()["tags"] == [
        {"key": "env", "value": "demo"},
        {"key": "owner", "value": "me"},
    ]

    second = client.put(
        url, json={"tags": [{"key": "team", "value": ""}, {"key": "env", "value": "prod"}]}
    )
    assert second.json()["tags"] == [
        {"key": "env", "value": "prod"},
        {"key": "team", "value": ""},
    ]
    assert client.get(f"{ZONES}/{zone['id']}").json()["tags"] == second.json()["tags"]

    assert client.put(url, json={"tags": []}).json() == {"tags": []}


@pytest.mark.parametrize(
    ("tags", "status", "message"),
    [
        ([{"key": "a", "value": "1"}, {"key": "a", "value": "2"}], 400, "more than once"),
        ([{"key": "aws:reserved", "value": "1"}], 400, "cannot start with 'aws:'"),
        ([{"key": f"k{i}", "value": ""} for i in range(51)], 400, "at most 50 tags"),
        ([{"key": "", "value": "1"}], 422, "not valid"),
        ([{"key": "k" * 129, "value": "1"}], 422, "not valid"),
        ([{"key": "k", "value": "v" * 257}], 422, "not valid"),
    ],
)
def test_tag_rules(
    client: TestClient, zone: dict[str, Any], tags: list[dict[str, str]], status: int, message: str
) -> None:
    response = client.put(f"{ZONES}/{zone['id']}/tags", json={"tags": tags})
    assert response.status_code == status
    assert message in response.json()["message"]
