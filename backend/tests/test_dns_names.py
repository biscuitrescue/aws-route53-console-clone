import pytest

from app.domain.dns_names import (
    DnsNameError,
    normalize_record_name,
    normalize_zone_name,
    sort_key,
    to_absolute,
)

ZONE = "example.com."


@pytest.mark.parametrize(
    ("raw", "expected"),
    [
        ("example.com", "example.com."),
        ("Example.COM.", "example.com."),
        ("  sub.example.com  ", "sub.example.com."),
        ("2.0.192.in-addr.arpa", "2.0.192.in-addr.arpa."),
        ("localhost", "localhost."),
    ],
)
def test_zone_names_are_canonicalised(raw: str, expected: str) -> None:
    assert normalize_zone_name(raw) == expected


@pytest.mark.parametrize(
    "raw",
    [
        "",
        "   ",
        ".",
        "bad..name",
        "sp ace.com",
        "münchen.de",
        "*.example.com",
        "a*b.example.com",
        "a" * 64 + ".com",
        ".".join(["a" * 50] * 6),
    ],
)
def test_invalid_zone_names_are_rejected(raw: str) -> None:
    with pytest.raises(DnsNameError):
        normalize_zone_name(raw)


@pytest.mark.parametrize(
    "raw",
    ["my!zone.com", "a&b.com", "-leading.com", "trailing-.com", "_under.com", "a.*.example.com"],
)
def test_zone_names_accept_the_characters_route53_lists(raw: str) -> None:
    assert normalize_zone_name(raw) == f"{raw}."


@pytest.mark.parametrize(
    ("raw", "expected"),
    [
        ("", ZONE),
        ("@", ZONE),
        ("www", "www.example.com."),
        ("WWW", "www.example.com."),
        ("a.b", "a.b.example.com."),
        ("www.example.com", "www.example.com."),
        ("www.example.com.", "www.example.com."),
        ("example.com", ZONE),
        ("_sip._tcp", "_sip._tcp.example.com."),
        ("*", "*.example.com."),
        ("*.dev", "*.dev.example.com."),
        ("10", "10.example.com."),
    ],
)
def test_record_names_resolve_against_the_zone(raw: str, expected: str) -> None:
    assert normalize_record_name(raw, ZONE) == expected


def test_record_name_outside_the_zone_is_rejected() -> None:
    with pytest.raises(DnsNameError, match=r"not permitted in zone example\.com\."):
        normalize_record_name("www.example.org.", ZONE)


@pytest.mark.parametrize("raw", ["a..b", "*prod", "pro*d", "has space", "ümlaut"])
def test_malformed_record_names_are_rejected(raw: str) -> None:
    with pytest.raises(DnsNameError):
        normalize_record_name(raw, ZONE)


def test_an_asterisk_below_the_leftmost_label_is_a_literal() -> None:
    assert normalize_record_name("www.*", ZONE) == "www.*.example.com."


def test_sort_key_orders_like_route53() -> None:
    names = ["www.example.com.", "example.com.", "api.example.com.", "a.api.example.com."]
    assert sorted(names, key=sort_key) == [
        "example.com.",
        "api.example.com.",
        "a.api.example.com.",
        "www.example.com.",
    ]


@pytest.mark.parametrize(
    ("name", "expected"),
    [("@", ZONE), ("www", "www.example.com."), ("Mail.Example.NET.", "mail.example.net.")],
)
def test_to_absolute(name: str, expected: str) -> None:
    assert to_absolute(name, ZONE) == expected
