from typing import Any

import pytest
from fastapi.testclient import TestClient

from tests.conftest import API, create_record, create_zone

ONE_OF_EACH: list[tuple[str, str, list[str]]] = [
    ("www", "A", ["192.0.2.10"]),
    ("www", "AAAA", ["2001:db8::10"]),
    ("blog", "CNAME", ["www.example.com"]),
    ("", "TXT", ['"v=spf1 include:_spf.example.com ~all"']),
    ("", "MX", ["10 mail.example.com"]),
    ("api", "NS", ["ns-1.example.net"]),
    ("10", "PTR", ["www.example.com"]),
    ("_sip._tcp", "SRV", ["10 60 5060 sip.example.com"]),
    ("", "CAA", ['0 issue "amazon.com"']),
]


def _url(zone: dict[str, Any], suffix: str = "") -> str:
    return f"{API}/hostedzones/{zone['id']}/records{suffix}"


def _post(client: TestClient, zone: dict[str, Any], **payload: Any) -> Any:
    return client.post(_url(zone), json={"ttl": 300, **payload})


def _listed(client: TestClient, zone: dict[str, Any], **params: Any) -> list[str]:
    response = client.get(_url(zone), params=params)
    assert response.status_code == 200, response.text
    return [f"{item['name']} {item['type']}" for item in response.json()["items"]]


@pytest.fixture
def populated(client: TestClient, zone: dict[str, Any]) -> dict[str, Any]:
    for name, record_type, values in ONE_OF_EACH:
        create_record(client, zone["id"], name, record_type, values)
    return zone


@pytest.mark.parametrize(("name", "record_type", "values"), ONE_OF_EACH)
def test_every_supported_type_can_be_created(
    client: TestClient, zone: dict[str, Any], name: str, record_type: str, values: list[str]
) -> None:
    record = create_record(client, zone["id"], name, record_type, values)
    expected_name = f"{name}.example.com." if name else "example.com."
    assert record["name"] == expected_name
    assert record["type"] == record_type
    assert record["values"] == values
    assert record["ttl"] == 300
    assert record["routing_policy"] == "simple"
    assert record["alias"] is False
    assert record["set_identifier"] is None

    fetched = client.get(_url(zone, f"/{record['id']}"))
    assert fetched.status_code == 200
    assert fetched.json() == record


def test_records_are_listed_in_route53_order(client: TestClient, populated: dict[str, Any]) -> None:
    assert _listed(client, populated) == [
        "example.com. CAA",
        "example.com. MX",
        "example.com. NS",
        "example.com. SOA",
        "example.com. TXT",
        "10.example.com. PTR",
        "_sip._tcp.example.com. SRV",
        "api.example.com. NS",
        "blog.example.com. CNAME",
        "www.example.com. A",
        "www.example.com. AAAA",
    ]


def test_multiple_values_keep_their_order(client: TestClient, zone: dict[str, Any]) -> None:
    values = ["192.0.2.3", "192.0.2.1", "192.0.2.2"]
    record = create_record(client, zone["id"], "multi", "A", values)
    assert client.get(_url(zone, f"/{record['id']}")).json()["values"] == values


@pytest.mark.parametrize(
    ("payload", "field", "message"),
    [
        ({"name": "www", "type": "A", "values": ["999.1.1.1"]}, "values", "valid IPv4 address"),
        ({"name": "www", "type": "A", "values": []}, "values", "At least one value"),
        ({"name": "www", "type": "AAAA", "values": ["192.0.2.1"]}, "values", "valid IPv6"),
        ({"name": "www", "type": "TXT", "values": ["unquoted"]}, "values", "quotation marks"),
        ({"name": "www", "type": "MX", "values": ["mail.example.com"]}, "values", "2 fields"),
        ({"name": "www", "type": "SRV", "values": ["1 2 3"]}, "values", "4 fields"),
        ({"name": "www", "type": "CAA", "values": ["0 issue"]}, "values", "3 fields"),
        ({"name": "www", "type": "A", "values": ["192.0.2.1"], "ttl": -1}, "ttl", "TTL must be"),
        (
            {"name": "www", "type": "A", "values": ["192.0.2.1"], "ttl": 2147483648},
            "ttl",
            "TTL must be between 0 and 2147483647",
        ),
        ({"name": "www", "type": "A", "values": ["192.0.2.1"], "ttl": None}, "ttl", "required"),
        ({"name": "a..b", "type": "A", "values": ["192.0.2.1"]}, "name", "Domain label is empty"),
        (
            {"name": "www.example.org.", "type": "A", "values": ["192.0.2.1"]},
            "name",
            "RRSet with DNS name www.example.org. is not permitted in zone example.com.",
        ),
        (
            {"name": "", "type": "CNAME", "values": ["www.example.com"]},
            "type",
            "RRSet of type CNAME with DNS name example.com. is not permitted at apex",
        ),
        (
            {"name": "sub", "type": "SOA", "values": ["a.example.com. b.example.com. 1 2 3 4 5"]},
            "type",
            "only permitted at the zone apex",
        ),
    ],
)
def test_invalid_records_are_rejected(
    client: TestClient, zone: dict[str, Any], payload: dict[str, Any], field: str, message: str
) -> None:
    response = _post(client, zone, **payload)
    assert response.status_code == 400, response.text
    body = response.json()
    assert body["code"] == "InvalidInput"
    assert message in body["message"]
    assert body["details"] == [{"field": field, "message": body["message"]}]
    assert len(_listed(client, zone)) == 2


def test_unknown_record_type_fails_request_validation(
    client: TestClient, zone: dict[str, Any]
) -> None:
    response = _post(client, zone, name="www", type="HINFO", values=["x"])
    assert response.status_code == 422
    assert response.json()["details"][0]["field"] == "type"


def test_ttl_bounds_are_accepted(client: TestClient, zone: dict[str, Any]) -> None:
    assert _post(client, zone, name="low", type="A", values=["192.0.2.1"], ttl=0).status_code == 201
    high = _post(client, zone, name="high", type="A", values=["192.0.2.1"], ttl=2147483647)
    assert high.status_code == 201


def test_a_duplicate_record_is_a_conflict(client: TestClient, zone: dict[str, Any]) -> None:
    create_record(client, zone["id"], "www", "A", ["192.0.2.1"])
    response = _post(client, zone, name="WWW.example.com", type="A", values=["192.0.2.2"])
    assert response.status_code == 409
    assert response.json() == {
        "code": "RecordSetAlreadyExists",
        "message": "Tried to create resource record set "
        "[name='www.example.com.', type='A'] but it already exists",
        "details": [
            {
                "field": "name",
                "message": "Tried to create resource record set "
                "[name='www.example.com.', type='A'] but it already exists",
            }
        ],
    }


def test_a_second_apex_soa_or_ns_cannot_be_created(
    client: TestClient, zone: dict[str, Any]
) -> None:
    soa = _post(
        client, zone, name="", type="SOA", values=["a.example.com. b.example.com. 1 2 3 4 5"]
    )
    ns = _post(client, zone, name="", type="NS", values=["ns.example.net"])
    assert (soa.status_code, ns.status_code) == (409, 409)


def test_cname_cannot_join_a_name_that_has_other_records(
    client: TestClient, zone: dict[str, Any]
) -> None:
    create_record(client, zone["id"], "www", "A", ["192.0.2.1"])
    response = _post(client, zone, name="www", type="CNAME", values=["other.example.com"])
    assert response.status_code == 409
    assert response.json()["code"] == "RecordSetConflict"
    assert response.json()["message"] == (
        "RRSet of type CNAME with DNS name www.example.com. is not permitted as it conflicts "
        "with other records with the same DNS name in zone example.com."
    )


def test_other_records_cannot_join_a_name_that_has_a_cname(
    client: TestClient, zone: dict[str, Any]
) -> None:
    create_record(client, zone["id"], "blog", "CNAME", ["www.example.com"])
    response = _post(client, zone, name="blog", type="TXT", values=['"hello"'])
    assert response.status_code == 409
    assert response.json()["message"] == (
        "RRSet of type TXT with DNS name blog.example.com. is not permitted because a "
        "conflicting RRSet of type CNAME with the same DNS name already exists in zone "
        "example.com."
    )


def test_edit_changes_ttl_and_values(client: TestClient, zone: dict[str, Any]) -> None:
    record = create_record(client, zone["id"], "www", "A", ["192.0.2.1", "192.0.2.2"])
    response = client.patch(
        _url(zone, f"/{record['id']}"), json={"ttl": 60, "values": ["192.0.2.9"]}
    )
    assert response.status_code == 200
    body = response.json()
    assert (body["id"], body["ttl"], body["values"]) == (record["id"], 60, ["192.0.2.9"])
    assert body["name"] == "www.example.com."
    assert client.get(_url(zone, f"/{record['id']}")).json() == body


def test_edit_can_grow_the_value_list(client: TestClient, zone: dict[str, Any]) -> None:
    record = create_record(client, zone["id"], "www", "A", ["192.0.2.1"])
    values = ["192.0.2.5", "192.0.2.6", "192.0.2.7"]
    response = client.patch(_url(zone, f"/{record['id']}"), json={"values": values})
    assert response.json()["values"] == values


def test_edit_can_rename_and_retype(client: TestClient, zone: dict[str, Any]) -> None:
    record = create_record(client, zone["id"], "old", "A", ["192.0.2.1"])
    response = client.patch(
        _url(zone, f"/{record['id']}"),
        json={"name": "new", "type": "AAAA", "values": ["2001:db8::1"]},
    )
    assert response.status_code == 200
    assert (response.json()["name"], response.json()["type"]) == ("new.example.com.", "AAAA")
    assert "old.example.com. A" not in _listed(client, zone)


def test_edit_revalidates_the_whole_record(client: TestClient, zone: dict[str, Any]) -> None:
    record = create_record(client, zone["id"], "www", "A", ["192.0.2.1"])
    url = _url(zone, f"/{record['id']}")

    bad_value = client.patch(url, json={"values": ["not-an-ip"]})
    assert bad_value.status_code == 400
    assert bad_value.json()["details"][0]["field"] == "values"

    # Changing only the type leaves the IPv4 value behind, which is not valid AAAA data.
    bad_type = client.patch(url, json={"type": "AAAA"})
    assert bad_type.status_code == 400
    assert client.get(url).json() == record


def test_edit_cannot_collide_with_another_record(client: TestClient, zone: dict[str, Any]) -> None:
    create_record(client, zone["id"], "taken", "A", ["192.0.2.1"])
    record = create_record(client, zone["id"], "free", "A", ["192.0.2.2"])
    response = client.patch(_url(zone, f"/{record['id']}"), json={"name": "taken"})
    assert response.status_code == 409
    assert response.json()["code"] == "RecordSetAlreadyExists"


def test_the_apex_ns_and_soa_can_be_edited_but_not_moved(
    client: TestClient, zone: dict[str, Any]
) -> None:
    records = {item["type"]: item for item in client.get(_url(zone)).json()["items"]}

    edited = client.patch(_url(zone, f"/{records['NS']['id']}"), json={"ttl": 3600})
    assert edited.status_code == 200
    assert edited.json()["ttl"] == 3600

    renamed = client.patch(_url(zone, f"/{records['NS']['id']}"), json={"name": "sub"})
    assert renamed.status_code == 400
    assert renamed.json()["message"] == (
        "A HostedZone must contain at least one NS record for the zone itself."
    )

    retyped = client.patch(
        _url(zone, f"/{records['SOA']['id']}"), json={"type": "TXT", "values": ['"x"']}
    )
    assert retyped.status_code == 400
    assert retyped.json()["message"] == "A HostedZone must contain exactly one SOA record"


def test_delete_removes_a_record(client: TestClient, zone: dict[str, Any]) -> None:
    record = create_record(client, zone["id"], "www", "A", ["192.0.2.1"])
    assert client.delete(_url(zone, f"/{record['id']}")).status_code == 204
    assert client.get(_url(zone, f"/{record['id']}")).status_code == 404
    assert client.delete(_url(zone, f"/{record['id']}")).status_code == 404


def test_the_apex_ns_and_soa_cannot_be_deleted(client: TestClient, zone: dict[str, Any]) -> None:
    messages = {
        "NS": "A HostedZone must contain at least one NS record for the zone itself.",
        "SOA": "A HostedZone must contain exactly one SOA record",
    }
    for item in client.get(_url(zone)).json()["items"]:
        response = client.delete(_url(zone, f"/{item['id']}"))
        assert response.status_code == 400
        assert response.json() == {
            "code": "InvalidChangeBatch",
            "message": messages[item["type"]],
            "details": [],
        }
    assert len(_listed(client, zone)) == 2


def test_a_delegation_ns_record_can_be_deleted(client: TestClient, zone: dict[str, Any]) -> None:
    record = create_record(client, zone["id"], "sub", "NS", ["ns-1.example.net"])
    assert client.delete(_url(zone, f"/{record['id']}")).status_code == 204


def test_records_belong_to_their_zone(client: TestClient, zone: dict[str, Any]) -> None:
    other = create_zone(client, "other.com")
    record = create_record(client, zone["id"], "www", "A", ["192.0.2.1"])
    response = client.get(f"{API}/hostedzones/{other['id']}/records/{record['id']}")
    assert response.status_code == 404
    assert response.json()["code"] == "NoSuchRecordSet"
    assert client.get(f"{API}/hostedzones/Z404/records").json()["code"] == "NoSuchHostedZone"


@pytest.mark.parametrize(
    ("params", "expected"),
    [
        (
            {"search": "www"},
            [
                "10.example.com. PTR",
                "blog.example.com. CNAME",
                "www.example.com. A",
                "www.example.com. AAAA",
            ],
        ),
        ({"search": "2001:db8"}, ["www.example.com. AAAA"]),
        ({"search": "amazon"}, ["example.com. CAA", "example.com. SOA"]),
        ({"type": "A"}, ["www.example.com. A"]),
        ({"type": ["A", "AAAA"]}, ["www.example.com. A", "www.example.com. AAAA"]),
        ({"type": "NS", "search": "api"}, ["api.example.com. NS"]),
        ({"filter": "name:eq:www.example.com"}, ["www.example.com. A", "www.example.com. AAAA"]),
        ({"filter": "name:starts_with:_sip"}, ["_sip._tcp.example.com. SRV"]),
        ({"filter": "type:eq:mx"}, ["example.com. MX"]),
        ({"filter": "value:contains:mail"}, ["example.com. MX"]),
        ({"filter": "value:eq:192.0.2.10"}, ["www.example.com. A"]),
        ({"filter": "ttl:gt:300"}, ["example.com. NS", "example.com. SOA"]),
        ({"filter": "ttl:eq:900"}, ["example.com. SOA"]),
        ({"filter": "alias:eq:yes"}, []),
        ({"filter": "routing_policy:ne:simple"}, []),
        (
            {"filter": ["type:eq:A", "type:eq:PTR"], "filter_mode": "or"},
            ["10.example.com. PTR", "www.example.com. A"],
        ),
        ({"filter": ["name:contains:www", "type:ne:A"]}, ["www.example.com. AAAA"]),
        ({"filter": ["any:contains:www", "any:contains:blog"]}, ["blog.example.com. CNAME"]),
        ({"filter": ["any:contains:sip", "any:not_contains:_tcp"]}, []),
    ],
)
def test_search_and_filters(
    client: TestClient, populated: dict[str, Any], params: dict[str, Any], expected: list[str]
) -> None:
    assert _listed(client, populated, **params) == expected


def test_value_filter_can_be_negated(client: TestClient, populated: dict[str, Any]) -> None:
    listed = _listed(client, populated, filter="value:not_contains:example")
    assert "example.com. MX" not in listed
    assert "www.example.com. A" in listed


@pytest.mark.parametrize(
    ("params", "first", "last"),
    [
        ({"sort": "name"}, "example.com. CAA", "www.example.com. AAAA"),
        ({"sort": "name", "order": "desc"}, "www.example.com. A", "example.com. TXT"),
        ({"sort": "type"}, "www.example.com. A", "example.com. TXT"),
        ({"sort": "ttl", "order": "desc"}, "example.com. NS", "www.example.com. AAAA"),
    ],
)
def test_sorting(
    client: TestClient, populated: dict[str, Any], params: dict[str, Any], first: str, last: str
) -> None:
    listed = _listed(client, populated, **params)
    assert (listed[0], listed[-1]) == (first, last)


def test_pagination(client: TestClient, populated: dict[str, Any]) -> None:
    pages = [
        client.get(_url(populated), params={"page_size": 4, "page": page}).json()
        for page in (1, 2, 3)
    ]
    assert [len(page["items"]) for page in pages] == [4, 4, 3]
    assert {(page["total"], page["pages"]) for page in pages} == {(11, 3)}
    ids = [item["id"] for page in pages for item in page["items"]]
    assert len(set(ids)) == 11


def test_bad_list_parameters(client: TestClient, zone: dict[str, Any]) -> None:
    assert client.get(_url(zone), params={"filter": "colour:eq:red"}).status_code == 400
    assert client.get(_url(zone), params={"sort": "colour"}).status_code == 400
    assert client.get(_url(zone), params={"type": "HINFO"}).status_code == 422


def test_alias_record(client: TestClient, zone: dict[str, Any]) -> None:
    target = {"dns_name": "D111.CloudFront.net", "hosted_zone_id": "Z2FDTNDATAQYW2"}
    response = client.post(_url(zone), json={"name": "cdn", "type": "A", "alias_target": target})
    assert response.status_code == 201, response.text
    record = response.json()
    assert record["alias"] is True
    assert record["ttl"] is None
    assert record["values"] == []
    assert record["alias_target"] == {
        "dns_name": "d111.cloudfront.net.",
        "hosted_zone_id": "Z2FDTNDATAQYW2",
        "evaluate_target_health": False,
    }
    assert _listed(client, zone, filter="alias:eq:yes") == ["cdn.example.com. A"]
    assert _listed(client, zone, search="cloudfront") == ["cdn.example.com. A"]

    # Supplying values turns it back into an ordinary record.
    plain = client.patch(
        _url(zone, f"/{record['id']}"), json={"values": ["192.0.2.1"], "ttl": 300}
    ).json()
    assert (plain["alias"], plain["alias_target"], plain["values"]) == (False, None, ["192.0.2.1"])

    again = client.patch(_url(zone, f"/{record['id']}"), json={"alias_target": target}).json()
    assert (again["alias"], again["values"], again["ttl"]) == (True, [], None)


@pytest.mark.parametrize(
    ("payload", "field"),
    [
        (
            {"type": "NS", "alias_target": {"dns_name": "x.example.com", "hosted_zone_id": "Z1"}},
            "alias_target",
        ),
        (
            {
                "type": "A",
                "values": ["192.0.2.1"],
                "alias_target": {"dns_name": "x.example.com", "hosted_zone_id": "Z1"},
            },
            "values",
        ),
        (
            {"type": "A", "alias_target": {"dns_name": "bad..name", "hosted_zone_id": "Z1"}},
            "alias_target",
        ),
    ],
)
def test_alias_rules(
    client: TestClient, zone: dict[str, Any], payload: dict[str, Any], field: str
) -> None:
    response = client.post(_url(zone), json={"name": "cdn", **payload})
    assert response.status_code == 400
    assert response.json()["details"][0]["field"] == field


def test_weighted_records_share_a_name(client: TestClient, zone: dict[str, Any]) -> None:
    for identifier, weight in (("blue", 90), ("green", 10)):
        response = _post(
            client,
            zone,
            name="lb",
            type="A",
            values=["192.0.2.1"],
            routing_policy="weighted",
            set_identifier=identifier,
            weight=weight,
        )
        assert response.status_code == 201, response.text
        assert response.json()["set_identifier"] == identifier
        assert response.json()["weight"] == weight

    duplicate = _post(
        client,
        zone,
        name="lb",
        type="A",
        values=["192.0.2.3"],
        routing_policy="weighted",
        set_identifier="blue",
        weight=1,
    )
    assert duplicate.status_code == 409

    mixed = _post(client, zone, name="lb", type="A", values=["192.0.2.4"])
    assert mixed.status_code == 409
    assert "uses the weighted routing policy" in mixed.json()["message"]
    assert _listed(client, zone, filter="routing_policy:eq:weighted") == [
        "lb.example.com. A",
        "lb.example.com. A",
    ]


@pytest.mark.parametrize(
    ("payload", "field"),
    [
        ({"routing_policy": "weighted", "weight": 1}, "set_identifier"),
        ({"routing_policy": "weighted", "set_identifier": "a"}, "weight"),
        ({"routing_policy": "weighted", "set_identifier": "a", "weight": 256}, "weight"),
        ({"routing_policy": "latency", "set_identifier": "a", "region": "mars-1"}, "region"),
        ({"routing_policy": "failover", "set_identifier": "a"}, "failover"),
        ({"routing_policy": "geolocation", "set_identifier": "a"}, "geolocation"),
        (
            {
                "routing_policy": "geolocation",
                "set_identifier": "a",
                "geolocation": {"continent_code": "EU", "country_code": "DE"},
            },
            "geolocation",
        ),
        (
            {
                "routing_policy": "multivalue",
                "set_identifier": "a",
                "values": ["192.0.2.1", "192.0.2.2"],
            },
            "values",
        ),
    ],
)
def test_routing_policy_rules(
    client: TestClient, zone: dict[str, Any], payload: dict[str, Any], field: str
) -> None:
    body = {"name": "lb", "type": "A", "values": ["192.0.2.1"], **payload}
    response = _post(client, zone, **body)
    assert response.status_code == 400, response.text
    assert response.json()["details"][0]["field"] == field


@pytest.mark.parametrize(
    "payload",
    [
        {"routing_policy": "latency", "set_identifier": "a", "region": "eu-west-1"},
        {"routing_policy": "failover", "set_identifier": "a", "failover": "PRIMARY"},
        {
            "routing_policy": "geolocation",
            "set_identifier": "a",
            "geolocation": {"country_code": "us", "subdivision_code": "ca"},
        },
        {"routing_policy": "multivalue", "set_identifier": "a", "health_check_id": "abc-123"},
    ],
)
def test_routing_policies_are_stored(
    client: TestClient, zone: dict[str, Any], payload: dict[str, Any]
) -> None:
    response = _post(client, zone, name="lb", type="A", values=["192.0.2.1"], **payload)
    assert response.status_code == 201, response.text
    record = response.json()
    assert record["routing_policy"] == payload["routing_policy"]
    assert record["set_identifier"] == "a"
    if "geolocation" in payload:
        assert record["geolocation"] == {
            "continent_code": None,
            "country_code": "US",
            "subdivision_code": "CA",
        }


def test_only_one_primary_failover_record(client: TestClient, zone: dict[str, Any]) -> None:
    base = {"name": "lb", "type": "A", "values": ["192.0.2.1"], "routing_policy": "failover"}
    assert _post(client, zone, **base, set_identifier="a", failover="PRIMARY").status_code == 201
    second = _post(client, zone, **base, set_identifier="b", failover="PRIMARY")
    assert second.status_code == 409
    assert _post(client, zone, **base, set_identifier="b", failover="SECONDARY").status_code == 201


def test_ns_records_only_support_simple_routing(client: TestClient, zone: dict[str, Any]) -> None:
    response = _post(
        client,
        zone,
        name="sub",
        type="NS",
        values=["ns-1.example.net"],
        routing_policy="weighted",
        set_identifier="a",
        weight=1,
    )
    assert response.status_code == 400
    assert response.json()["message"] == "NS records support only the simple routing policy"


def test_switching_to_simple_routing_clears_the_policy_fields(
    client: TestClient, zone: dict[str, Any]
) -> None:
    record = _post(
        client,
        zone,
        name="lb",
        type="A",
        values=["192.0.2.1"],
        routing_policy="weighted",
        set_identifier="a",
        weight=5,
    ).json()
    simple = client.patch(_url(zone, f"/{record['id']}"), json={"routing_policy": "simple"}).json()
    assert (simple["routing_policy"], simple["set_identifier"], simple["weight"]) == (
        "simple",
        None,
        None,
    )
