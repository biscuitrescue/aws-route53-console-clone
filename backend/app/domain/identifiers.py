"""Generators for Route 53 style identifiers and delegation sets."""

import secrets
import string
import uuid

from app.domain.enums import ZoneType

_ZONE_ID_ALPHABET = string.ascii_uppercase + string.digits
_ZONE_ID_RANDOM_LENGTH = 20
_SOA_SUFFIX = "awsdns-hostmaster.amazon.com. 1 7200 900 1209600 86400"

# Each TLD owns a block of 512 name-server numbers, as in real delegation sets.
_DELEGATION_BLOCKS: tuple[tuple[str, int], ...] = (
    ("co.uk", 1536),
    ("com", 0),
    ("org", 1024),
    ("net", 512),
)

APEX_SOA_TTL = 900
APEX_NS_TTL = 172_800


def new_hosted_zone_id() -> str:
    return "Z" + "".join(secrets.choice(_ZONE_ID_ALPHABET) for _ in range(_ZONE_ID_RANDOM_LENGTH))


def new_record_id() -> str:
    return str(uuid.uuid4())


def new_caller_reference() -> str:
    return str(uuid.uuid4())


def new_delegation_set(zone_type: ZoneType) -> list[str]:
    """Four authoritative name servers. Private zones always get Route 53's fixed set."""
    if zone_type is ZoneType.PRIVATE:
        return [f"ns-{start}.awsdns-00.{tld}." for tld, start in _DELEGATION_BLOCKS]
    return [
        f"ns-{start + secrets.randbelow(512)}.awsdns-{secrets.randbelow(64):02d}.{tld}."
        for tld, start in _DELEGATION_BLOCKS
    ]


def soa_value(primary_name_server: str) -> str:
    return f"{primary_name_server} {_SOA_SUFFIX}"
