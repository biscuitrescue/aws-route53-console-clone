"""Enumerations shared by models, schemas and services."""

from enum import StrEnum


class ZoneType(StrEnum):
    PUBLIC = "public"
    PRIVATE = "private"


class RecordType(StrEnum):
    A = "A"
    AAAA = "AAAA"
    CAA = "CAA"
    CNAME = "CNAME"
    MX = "MX"
    NS = "NS"
    PTR = "PTR"
    SOA = "SOA"
    SRV = "SRV"
    TXT = "TXT"


class RoutingPolicy(StrEnum):
    SIMPLE = "simple"
    WEIGHTED = "weighted"
    LATENCY = "latency"
    FAILOVER = "failover"
    GEOLOCATION = "geolocation"
    MULTIVALUE = "multivalue"


class FailoverRole(StrEnum):
    PRIMARY = "PRIMARY"
    SECONDARY = "SECONDARY"


class ChangeAction(StrEnum):
    CREATE = "CREATE"
    UPSERT = "UPSERT"
    DELETE = "DELETE"


def sql_in_list(enum: type[StrEnum]) -> str:
    """Render enum values as a SQL ``IN`` list for CHECK constraints."""
    return ", ".join(f"'{member.value}'" for member in enum)
