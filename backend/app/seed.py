"""Idempotent demo data: the demo user plus a realistic set of zones and records.

Run with ``python -m app.seed`` after ``alembic upgrade head``. Running it again never
duplicates or overwrites anything.
"""

import logging
from dataclasses import dataclass

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.config import Settings, get_settings
from app.db import create_db_engine, create_session_factory
from app.domain.enums import ChangeAction, RecordType, RoutingPolicy, ZoneType
from app.models import User
from app.repositories import hosted_zones as zone_repository
from app.schemas.hosted_zone import HostedZoneCreate, Tag, VpcAssociation
from app.schemas.record_set import AliasTarget, Change, RecordSetInput
from app.services import hosted_zones as zone_service
from app.services import records as record_service
from app.services import sandbox as sandbox_service
from app.services.auth import hash_password

logger = logging.getLogger(__name__)

_CLOUDFRONT_ZONE_ID = "Z2FDTNDATAQYW2"


def _record(
    name: str, record_type: RecordType, values: list[str], ttl: int = 300
) -> RecordSetInput:
    return RecordSetInput(name=name, type=record_type, ttl=ttl, values=values)


@dataclass(frozen=True, slots=True)
class _SeedZone:
    name: str
    description: str = ""
    type: ZoneType = ZoneType.PUBLIC
    vpcs: tuple[tuple[str, str], ...] = ()
    tags: tuple[tuple[str, str], ...] = ()
    records: tuple[RecordSetInput, ...] = ()


_EXAMPLE_COM_HOSTS = {
    "app": "192.0.2.21",
    "api": "192.0.2.22",
    "admin": "192.0.2.23",
    "auth": "192.0.2.24",
    "billing": "192.0.2.25",
    "docs": "192.0.2.26",
    "grafana": "192.0.2.27",
    "jenkins": "192.0.2.28",
    "kibana": "192.0.2.29",
    "mail": "192.0.2.30",
    "monitor": "192.0.2.31",
    "portal": "192.0.2.32",
    "search": "192.0.2.33",
    "staging": "192.0.2.34",
    "status": "192.0.2.35",
    "vpn": "192.0.2.36",
}

_SEED_ZONES: tuple[_SeedZone, ...] = (
    _SeedZone(
        name="example.com",
        description="Primary corporate domain",
        tags=(("environment", "production"), ("team", "platform")),
        records=(
            _record("", RecordType.A, ["192.0.2.10"]),
            _record("", RecordType.MX, ["10 mail.example.com", "20 mail2.example.com"], 3600),
            _record(
                "",
                RecordType.TXT,
                ['"v=spf1 include:_spf.example.com ~all"', '"google-site-verification=r53clone"'],
                3600,
            ),
            _record("", RecordType.CAA, ['0 issue "amazon.com"', '0 issuewild ";"'], 3600),
            _record("www", RecordType.A, ["192.0.2.10", "192.0.2.11"]),
            _record("www", RecordType.AAAA, ["2001:db8::10"]),
            _record("blog", RecordType.CNAME, ["www.example.com"]),
            _record("shop", RecordType.CNAME, ["example-shop.net"]),
            _record("dev", RecordType.NS, ["ns-1.example.net", "ns-2.example.net"], 172800),
            _record("_sip._tcp", RecordType.SRV, ["10 60 5060 sip.example.com"], 3600),
            _record("_dmarc", RecordType.TXT, ['"v=DMARC1; p=quarantine"'], 3600),
            _record("*.preview", RecordType.A, ["192.0.2.60"], 60),
            _record("", RecordType.SPF, ['"v=spf1 include:_spf.example.com ~all"'], 3600),
            _record("", RecordType.HTTPS, ['1 . alpn="h3,h2" ipv4hint="192.0.2.10"'], 3600),
            _record("_dns.resolver", RecordType.SVCB, ['1 doh.example.com alpn="h2" port=443']),
            _record(
                "sip",
                RecordType.NAPTR,
                [
                    '10 100 "S" "SIP+D2T" "" _sip._tcp.example.com',
                    '20 100 "S" "SIP+D2U" "" _sip._udp.example.com',
                ],
                3600,
            ),
            # The DS of the delegated "dev" subdomain, next to its NS records.
            _record(
                "dev",
                RecordType.DS,
                ["12345 13 2 9f86d081884c7d659a2feaa0c55ad015a3bf4f1b2b0b822cd15d6c15b0f00a08"],
                3600,
            ),
            _record(
                "_443._tcp.www",
                RecordType.TLSA,
                ["3 1 1 d2abde240d7cd3ee6b4b28c54df034b97983a1d16e8a410e4561cb106618e971"],
                3600,
            ),
            _record(
                "bastion",
                RecordType.SSHFP,
                [
                    "4 2 5e884898da28047151d0e56f8dc6292773603d0d6aabbdd62a11ef721d1542d8",
                    "1 1 09f6a01d2175742b257c6b98b7c72c44c4040683",
                ],
                3600,
            ),
            RecordSetInput(
                name="cdn",
                type=RecordType.A,
                alias_target=AliasTarget(
                    dns_name="d111111abcdef8.cloudfront.net",
                    hosted_zone_id=_CLOUDFRONT_ZONE_ID,
                ),
            ),
            RecordSetInput(
                name="lb",
                type=RecordType.A,
                ttl=60,
                values=["192.0.2.41"],
                routing_policy=RoutingPolicy.WEIGHTED,
                set_identifier="blue",
                weight=90,
            ),
            RecordSetInput(
                name="lb",
                type=RecordType.A,
                ttl=60,
                values=["192.0.2.42"],
                routing_policy=RoutingPolicy.WEIGHTED,
                set_identifier="green",
                weight=10,
            ),
            *(
                _record(host, RecordType.A, [address])
                for host, address in _EXAMPLE_COM_HOSTS.items()
            ),
        ),
    ),
    _SeedZone(
        name="example-shop.net",
        description="Storefront",
        tags=(("environment", "production"),),
        records=(
            _record("", RecordType.A, ["198.51.100.20"]),
            _record("www", RecordType.CNAME, ["example-shop.net"]),
            _record("", RecordType.MX, ["10 inbound-smtp.example-shop.net"], 3600),
            _record("", RecordType.TXT, ['"v=spf1 -all"'], 3600),
        ),
    ),
    _SeedZone(
        name="api.example.com",
        description="Delegated subdomain for the public API",
        records=(
            _record("", RecordType.A, ["203.0.113.5"]),
            _record("v1", RecordType.A, ["203.0.113.6"]),
            _record("v2", RecordType.A, ["203.0.113.7"]),
        ),
    ),
    _SeedZone(
        name="internal.example.corp",
        description="Private zone for service discovery",
        type=ZoneType.PRIVATE,
        vpcs=(("vpc-0a1b2c3d4e5f67890", "us-east-1"),),
        tags=(("environment", "production"), ("visibility", "internal")),
        records=(
            _record("db", RecordType.A, ["10.0.12.5"], 60),
            _record("cache", RecordType.A, ["10.0.12.6"], 60),
            _record("queue", RecordType.CNAME, ["sqs.us-east-1.amazonaws.com"], 60),
        ),
    ),
    _SeedZone(
        name="2.0.192.in-addr.arpa",
        description="Reverse lookups for 192.0.2.0/24",
        records=(
            _record("10", RecordType.PTR, ["www.example.com"], 3600),
            _record("30", RecordType.PTR, ["mail.example.com"], 3600),
        ),
    ),
    _SeedZone(name="example.org", description="Foundation website"),
    _SeedZone(name="example.io", description="Developer portal"),
    _SeedZone(name="dev-sandbox.net", tags=(("environment", "development"),)),
    _SeedZone(name="staging.example-shop.net", description="Storefront staging"),
    _SeedZone(name="analytics.example.com", description="Tracking and reporting endpoints"),
    _SeedZone(name="media-assets.net", description="Static assets"),
    _SeedZone(
        name="corp.example.internal",
        description="Office network",
        type=ZoneType.PRIVATE,
        vpcs=(("vpc-1f2e3d4c", "eu-west-1"),),
    ),
)


def ensure_demo_user(db: Session, settings: Settings) -> User:
    email = settings.demo_email.strip().lower()
    user = db.scalar(select(User).where(User.email == email))
    if user is None:
        user = User(
            email=email,
            password_hash=hash_password(settings.demo_password),
            display_name=settings.demo_display_name,
            account_id=settings.demo_account_id,
        )
        db.add(user)
        db.commit()
        logger.info("Created demo user %s", email)
    return user


def seed_demo_zones(db: Session, user: User) -> int:
    """Create the demo zones for a user who has none; returns how many were created."""
    if zone_repository.count_owned(db, user.id):
        return 0
    for seed_zone in _SEED_ZONES:
        row = zone_service.create_zone(
            db,
            user,
            HostedZoneCreate(
                name=seed_zone.name,
                description=seed_zone.description,
                type=seed_zone.type,
                vpcs=[VpcAssociation(vpc_id=vpc, region=region) for vpc, region in seed_zone.vpcs],
                tags=[Tag(key=key, value=value) for key, value in seed_zone.tags],
            ),
        )
        if seed_zone.records:
            record_service.apply_batch(
                db,
                row.zone,
                [
                    Change(action=ChangeAction.CREATE, record_set=record)
                    for record in seed_zone.records
                ],
            )
    return len(_SEED_ZONES)


def seed(db: Session, settings: Settings) -> None:
    """Make sure the demo user and the sample zones exist.

    With sandboxes on, the zones belong to the template that every sandbox is copied
    from; otherwise to the demo user itself.
    """
    owner = ensure_demo_user(db, settings)
    if settings.demo_sandbox:
        owner = sandbox_service.ensure_template(db)
    if settings.seed_demo_data:
        created = seed_demo_zones(db, owner)
        logger.info("Seeded %d demo hosted zones", created)


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")
    settings = get_settings()
    engine = create_db_engine(settings.database_url)
    with create_session_factory(engine)() as db:
        seed(db, settings)
    engine.dispose()


if __name__ == "__main__":
    main()
