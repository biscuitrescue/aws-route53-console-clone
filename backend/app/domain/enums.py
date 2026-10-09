"""Enumerations shared by models, schemas and services."""

from enum import StrEnum


class UserKind(StrEnum):
    """What a row of ``users`` is: a sign-in account, or data that hangs off one."""

    ACCOUNT = "account"
    # Owns the canonical sample zones that every sandbox starts as a copy of.
    TEMPLATE = "template"
    # One visitor's private copy of the shared account.
    SANDBOX = "sandbox"


class ZoneType(StrEnum):
    PUBLIC = "public"
    PRIVATE = "private"


class RecordType(StrEnum):
    A = "A"
    AAAA = "AAAA"
    CAA = "CAA"
    CNAME = "CNAME"
    DS = "DS"
    HTTPS = "HTTPS"
    MX = "MX"
    NAPTR = "NAPTR"
    NS = "NS"
    PTR = "PTR"
    SOA = "SOA"
    SPF = "SPF"
    SRV = "SRV"
    SSHFP = "SSHFP"
    SVCB = "SVCB"
    TLSA = "TLSA"
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


class ChangeStatus(StrEnum):
    PENDING = "PENDING"
    INSYNC = "INSYNC"


class ChangeAction(StrEnum):
    CREATE = "CREATE"
    UPSERT = "UPSERT"
    DELETE = "DELETE"


def sql_in_list(enum: type[StrEnum]) -> str:
    """Render enum values as a SQL ``IN`` list for CHECK constraints."""
    return ", ".join(f"'{member.value}'" for member in enum)
