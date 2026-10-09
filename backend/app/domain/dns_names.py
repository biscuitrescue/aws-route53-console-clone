"""DNS name normalisation and validation.

Names are stored canonically: lowercase, fully qualified, with a trailing dot.
"""

import re

MAX_NAME_LENGTH = 253
MAX_LABEL_LENGTH = 63
WILDCARD = "*"

# Route 53 accepts these characters in the names of hosted zones and records; the console
# lists them under the "Domain name" field. Anything else (spaces, non-ASCII) is rejected.
_LABEL_RE = re.compile(r"""^[a-z0-9!"#$%&'()*+,\-/:;<=>?@\[\\\]^_`{|}~]+$""")


class DnsNameError(ValueError):
    """Raised when a domain name is malformed."""


def _problem(code: str, description: str, name: str) -> DnsNameError:
    """Route 53's wording: ``DomainLabelEmpty (Domain label is empty) encountered with 'a..b'``."""
    return DnsNameError(f"{code} ({description}) encountered with '{name}'")


def _validate_labels(name: str, *, allow_wildcard: bool) -> None:
    """Check each label.

    An asterisk is a wildcard only as the whole leftmost label of a record name. It is
    not allowed anywhere in the leftmost label of a hosted zone name, and in any other
    position Route 53 treats it as a literal character.
    """
    for position, label in enumerate(name.split(".")):
        if not label:
            raise _problem("DomainLabelEmpty", "Domain label is empty", name)
        if len(label) > MAX_LABEL_LENGTH:
            raise _problem("DomainLabelTooLong", "Domain label is too long", name)
        if not _LABEL_RE.match(label):
            raise _problem("InvalidDomainName", "Domain name contains invalid characters", name)
        if position == 0 and WILDCARD in label and not (allow_wildcard and label == WILDCARD):
            raise _problem(
                "InvalidDomainName",
                "An asterisk in the leftmost label must be the whole label"
                if allow_wildcard
                else "The leftmost label cannot contain an asterisk",
                name,
            )


def _canonical(raw: str, *, allow_wildcard: bool) -> str:
    name = raw.strip().lower().removesuffix(".")
    if not name:
        raise DnsNameError("Domain name is empty.")
    if len(name) > MAX_NAME_LENGTH:
        raise _problem("DomainNameTooLong", "Domain name is too long", name)
    _validate_labels(name, allow_wildcard=allow_wildcard)
    return f"{name}."


def normalize_zone_name(raw: str) -> str:
    """Return the canonical form of a hosted zone name."""
    return _canonical(raw, allow_wildcard=False)


def is_within_zone(name: str, zone_name: str) -> bool:
    """Whether a canonical name is the zone apex or a descendant of it."""
    return name == zone_name or name.endswith(f".{zone_name}")


def normalize_record_name(raw: str, zone_name: str) -> str:
    """Resolve a record name against its zone and return the canonical FQDN.

    Accepts the apex (empty string or ``@``), a name relative to the zone (``www``) or a
    fully qualified name with or without the trailing dot. Like Route 53, a name that
    already ends with the zone name is treated as fully qualified.
    """
    name = raw.strip().lower()
    if name in ("", "@"):
        return zone_name

    bare_zone = zone_name.removesuffix(".")
    if name.endswith("."):
        candidate = name
    elif name == bare_zone or name.endswith(f".{bare_zone}"):
        candidate = f"{name}."
    else:
        candidate = f"{name}.{zone_name}"

    canonical = _canonical(candidate, allow_wildcard=True)
    if not is_within_zone(canonical, zone_name):
        raise DnsNameError(f"RRSet with DNS name {canonical} is not permitted in zone {zone_name}")
    return canonical


def validate_hostname(value: str, *, allow_root: bool = False) -> None:
    """Validate a host name used as record data (CNAME target, MX exchange, ...)."""
    if allow_root and value == ".":
        return
    _canonical(value, allow_wildcard=False)


def to_absolute(name: str, origin: str) -> str:
    """Resolve a zone-file name against ``origin``; returns a lowercase FQDN with trailing dot."""
    name = name.lower()
    if name == "@":
        return origin
    if name.endswith("."):
        return name
    return f"{name}." if origin == "." else f"{name}.{origin}"


def is_wildcard(name: str) -> bool:
    """Whether a canonical record name is a wildcard such as ``*.example.com.``."""
    return name.startswith(f"{WILDCARD}.")


def sort_key(name: str) -> str:
    """Key that orders names the way Route 53 lists them: by labels, right to left."""
    return ".".join(reversed(name.removesuffix(".").split(".")))
