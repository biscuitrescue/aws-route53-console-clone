from typing import Any

from fastapi.testclient import TestClient

from tests.conftest import API, create_record


def _records_url(zone: dict[str, Any]) -> str:
    return f"{API}/hostedzones/{zone['id']}/records"


def _batch(client: TestClient, zone: dict[str, Any], *changes: dict[str, Any], **extra: Any) -> Any:
    return client.post(f"{_records_url(zone)}:batch", json={"changes": list(changes), **extra})


def _change(
    action: str, name: str, record_type: str, values: list[str], **fields: Any
) -> dict[str, Any]:
    record_set = {"name": name, "type": record_type, "ttl": 300, "values": values, **fields}
    return {"action": action, "record_set": record_set}


def _snapshot(client: TestClient, zone: dict[str, Any]) -> list[tuple[str, str, int, list[str]]]:
    items = client.get(_records_url(zone), params={"page_size": 500}).json()["items"]
    return [(item["name"], item["type"], item["ttl"], item["values"]) for item in items]


def test_a_batch_creates_updates_and_deletes_together(
    client: TestClient, zone: dict[str, Any]
) -> None:
    create_record(client, zone["id"], "old", "A", ["192.0.2.1"])
    create_record(client, zone["id"], "www", "A", ["192.0.2.2"])

    response = _batch(
        client,
        zone,
        _change("CREATE", "new", "A", ["192.0.2.3"]),
        _change("UPSERT", "www", "A", ["192.0.2.20", "192.0.2.21"], ttl=60),
        _change("UPSERT", "fresh", "TXT", ['"hello"']),
        _change("DELETE", "old", "A", ["192.0.2.1"]),
        comment="deploy 42",
    )
    assert response.status_code == 200, response.text
    body = response.json()
    assert (body["status"], body["comment"]) == ("PENDING", "deploy 42")
    assert (body["created"], body["updated"], body["deleted"]) == (2, 1, 1)
    assert [record["name"] for record in body["record_sets"]] == [
        "new.example.com.",
        "www.example.com.",
        "fresh.example.com.",
    ]

    snapshot = _snapshot(client, zone)
    assert ("www.example.com.", "A", 60, ["192.0.2.20", "192.0.2.21"]) in snapshot
    assert ("new.example.com.", "A", 300, ["192.0.2.3"]) in snapshot
    assert ("fresh.example.com.", "TXT", 300, ['"hello"']) in snapshot
    assert all(name != "old.example.com." for name, *_rest in snapshot)


def test_upsert_keeps_the_record_id(client: TestClient, zone: dict[str, Any]) -> None:
    record = create_record(client, zone["id"], "www", "A", ["192.0.2.1"])
    body = _batch(client, zone, _change("UPSERT", "www", "A", ["192.0.2.9"])).json()
    assert body["record_sets"][0]["id"] == record["id"]


def test_one_bad_change_rolls_back_the_whole_batch(
    client: TestClient, zone: dict[str, Any]
) -> None:
    create_record(client, zone["id"], "keep", "A", ["192.0.2.1"])
    before = _snapshot(client, zone)

    response = _batch(
        client,
        zone,
        _change("CREATE", "one", "A", ["192.0.2.2"]),
        _change("DELETE", "keep", "A", ["192.0.2.1"]),
        _change("UPSERT", "keep2", "A", ["192.0.2.3"]),
        _change("CREATE", "broken", "A", ["999.1.1.1"]),
    )
    assert response.status_code == 400
    body = response.json()
    assert body["code"] == "InvalidChangeBatch"
    assert "valid IPv4 address" in body["message"]
    assert body["details"] == [{"index": 3, "field": "values", "message": body["message"]}]

    assert _snapshot(client, zone) == before


def test_every_failing_change_is_reported(client: TestClient, zone: dict[str, Any]) -> None:
    create_record(client, zone["id"], "www", "A", ["192.0.2.1"])
    response = _batch(
        client,
        zone,
        _change("CREATE", "www", "A", ["192.0.2.2"]),
        _change("CREATE", "ok", "A", ["192.0.2.3"]),
        _change("DELETE", "ghost", "A", []),
    )
    assert response.status_code == 400
    body = response.json()
    assert [detail["index"] for detail in body["details"]] == [0, 2]
    assert body["message"] == (
        "[Tried to create resource record set [name='www.example.com.', type='A'] "
        "but it already exists, Tried to delete resource record set "
        "[name='ghost.example.com.', type='A'] but it was not found]"
    )
    assert all(name != "ok.example.com." for name, *_rest in _snapshot(client, zone))


def test_later_changes_see_earlier_ones(client: TestClient, zone: dict[str, Any]) -> None:
    create_record(client, zone["id"], "www", "A", ["192.0.2.1"])

    replaced = _batch(
        client,
        zone,
        _change("DELETE", "www", "A", ["192.0.2.1"]),
        _change("CREATE", "www", "CNAME", ["target.example.com"]),
    )
    assert replaced.status_code == 200, replaced.text

    twice = _batch(
        client,
        zone,
        _change("CREATE", "dup", "A", ["192.0.2.1"]),
        _change("CREATE", "dup", "A", ["192.0.2.2"]),
    )
    assert twice.status_code == 400
    assert [detail["index"] for detail in twice.json()["details"]] == [1]


def test_cname_conflicts_apply_inside_a_batch(client: TestClient, zone: dict[str, Any]) -> None:
    response = _batch(
        client,
        zone,
        _change("CREATE", "www", "A", ["192.0.2.1"]),
        _change("CREATE", "www", "CNAME", ["other.example.com"]),
    )
    assert response.status_code == 400
    assert "conflicts with other records" in response.json()["message"]
    assert len(_snapshot(client, zone)) == 2


def test_delete_must_match_the_current_values(client: TestClient, zone: dict[str, Any]) -> None:
    create_record(client, zone["id"], "www", "A", ["192.0.2.1", "192.0.2.2"])

    wrong_values = _batch(client, zone, _change("DELETE", "www", "A", ["192.0.2.9"]))
    assert wrong_values.status_code == 400
    assert wrong_values.json()["message"] == (
        "Tried to delete resource record set [name='www.example.com.', type='A'] "
        "but the values provided do not match the current values"
    )

    wrong_ttl = _batch(client, zone, _change("DELETE", "www", "A", [], ttl=60))
    assert wrong_ttl.status_code == 400

    matching = _batch(client, zone, _change("DELETE", "www", "A", ["192.0.2.2", "192.0.2.1"]))
    assert matching.status_code == 200
    assert matching.json()["deleted"] == 1


def test_bulk_delete_by_identity(client: TestClient, zone: dict[str, Any]) -> None:
    for host in ("a", "b", "c"):
        create_record(client, zone["id"], host, "A", ["192.0.2.1"])
    response = _batch(
        client,
        zone,
        *({"action": "DELETE", "record_set": {"name": host, "type": "A"}} for host in ("a", "b")),
    )
    assert response.status_code == 200
    assert response.json()["deleted"] == 2
    assert [name for name, *_rest in _snapshot(client, zone)] == [
        "example.com.",
        "example.com.",
        "c.example.com.",
    ]


def test_the_apex_ns_and_soa_survive_a_batch(client: TestClient, zone: dict[str, Any]) -> None:
    before = _snapshot(client, zone)
    response = _batch(
        client,
        zone,
        {"action": "DELETE", "record_set": {"name": "", "type": "SOA"}},
        {"action": "DELETE", "record_set": {"name": "", "type": "NS"}},
    )
    assert response.status_code == 400
    assert [detail["message"] for detail in response.json()["details"]] == [
        "A HostedZone must contain exactly one SOA record",
        "A HostedZone must contain at least one NS record for the zone itself.",
    ]
    assert _snapshot(client, zone) == before

    edited = _batch(client, zone, _change("UPSERT", "", "NS", ["ns-1.example.net."], ttl=3600))
    assert edited.status_code == 200
    assert ("example.com.", "NS", 3600, ["ns-1.example.net."]) in _snapshot(client, zone)


def test_weighted_records_are_addressed_by_set_identifier(
    client: TestClient, zone: dict[str, Any]
) -> None:
    def weighted(action: str, identifier: str, weight: int) -> dict[str, Any]:
        return _change(
            action,
            "lb",
            "A",
            ["192.0.2.1"],
            routing_policy="weighted",
            set_identifier=identifier,
            weight=weight,
        )

    created = _batch(client, zone, weighted("CREATE", "blue", 1), weighted("CREATE", "green", 1))
    assert created.status_code == 200, created.text

    changed = _batch(client, zone, weighted("UPSERT", "blue", 200), weighted("DELETE", "green", 1))
    assert changed.status_code == 200, changed.text
    assert (changed.json()["updated"], changed.json()["deleted"]) == (1, 1)

    items = client.get(_records_url(zone), params={"filter": "name:eq:lb.example.com"}).json()
    assert [(item["set_identifier"], item["weight"]) for item in items["items"]] == [("blue", 200)]


def test_an_empty_or_malformed_batch_is_rejected(client: TestClient, zone: dict[str, Any]) -> None:
    assert _batch(client, zone).status_code == 422
    bad_action = _batch(client, zone, _change("REPLACE", "www", "A", ["192.0.2.1"]))
    assert bad_action.status_code == 422
    assert bad_action.json()["details"][0]["field"] == "changes.0.action"


def test_a_batch_aligns_the_ttl_of_a_routed_group(client: TestClient, zone: dict[str, Any]) -> None:
    def weighted(identifier: str, ttl: int) -> dict[str, Any]:
        return _change(
            "CREATE",
            "lb",
            "A",
            ["192.0.2.1"],
            ttl=ttl,
            routing_policy="weighted",
            set_identifier=identifier,
            weight=1,
        )

    assert _batch(client, zone, weighted("a", 300), weighted("b", 60)).status_code == 200
    items = client.get(_records_url(zone), params={"filter": "name:eq:lb.example.com"}).json()
    assert {item["ttl"] for item in items["items"]} == {60}
