"""BIND zone file parsing and rendering (RFC 1035 master file format)."""

import re
from collections.abc import Iterable, Iterator
from dataclasses import dataclass, field

from app.domain.dns_names import DnsNameError, normalize_record_name, to_absolute
from app.domain.enums import RecordType
from app.domain.record_validation import RecordValueError, validate_values

DEFAULT_TTL = 300

_TTL_RE = re.compile(r"^(\d+[wdhms]?)+$", re.IGNORECASE)
_TTL_PART_RE = re.compile(r"(\d+)([wdhms]?)", re.IGNORECASE)
_TTL_UNITS = {"": 1, "s": 1, "m": 60, "h": 3600, "d": 86_400, "w": 604_800}
_SUPPORTED_CLASS = "IN"
_OTHER_CLASSES = frozenset({"CH", "CS", "HS"})
_TOKEN_BREAKS = frozenset(' \t;()"')


@dataclass(frozen=True, slots=True)
class Token:
    text: str
    quoted: bool = False


@dataclass(frozen=True, slots=True)
class ZoneFileIssue:
    line: int
    message: str


@dataclass(slots=True)
class ParsedRecordSet:
    name: str
    type: RecordType
    ttl: int
    values: list[str]
    line: int


@dataclass(slots=True)
class ParsedZoneFile:
    record_sets: list[ParsedRecordSet] = field(default_factory=list)
    issues: list[ZoneFileIssue] = field(default_factory=list)


class _LineError(Exception):
    """A problem confined to one logical line of the zone file."""


def parse_ttl(text: str) -> int:
    """Parse a TTL in seconds or BIND units (``1h30m``, ``2d``, ``1w``)."""
    if not _TTL_RE.match(text):
        raise _LineError(f"Invalid TTL '{text}'")
    return sum(
        int(amount) * _TTL_UNITS[unit.lower()] for amount, unit in _TTL_PART_RE.findall(text)
    )


def _tokenize_line(raw: str, tokens: list[Token], depth: int) -> int:
    """Append the tokens of one physical line; returns the new parenthesis depth."""
    position, length = 0, len(raw)
    while position < length:
        char = raw[position]
        if char in " \t":
            position += 1
        elif char == ";":
            break
        elif char == "(":
            depth += 1
            position += 1
        elif char == ")":
            if depth == 0:
                raise _LineError("Unbalanced closing parenthesis")
            depth -= 1
            position += 1
        elif char == '"':
            end = position + 1
            while end < length and raw[end] != '"':
                end += 2 if raw[end] == "\\" else 1
            if end >= length:
                raise _LineError("Unterminated quoted string")
            tokens.append(Token(raw[position + 1 : end], quoted=True))
            position = end + 1
        else:
            end = position
            while end < length and raw[end] not in _TOKEN_BREAKS:
                end += 2 if raw[end] == "\\" else 1
            tokens.append(Token(raw[position:end]))
            position = end
    return depth


def _logical_lines(
    text: str, issues: list[ZoneFileIssue]
) -> Iterator[tuple[int, bool, list[Token]]]:
    """Yield ``(line number, starts with blank, tokens)`` with parentheses joined."""
    depth = 0
    tokens: list[Token] = []
    start_line = 0
    starts_blank = False
    for line_number, raw in enumerate(text.splitlines(), start=1):
        if depth == 0:
            tokens, start_line, starts_blank = [], line_number, raw[:1] in (" ", "\t")
        try:
            depth = _tokenize_line(raw, tokens, depth)
        except _LineError as exc:
            issues.append(ZoneFileIssue(line_number, str(exc)))
            depth, tokens = 0, []
            continue
        if depth == 0 and tokens:
            yield start_line, starts_blank, tokens
    if depth:
        issues.append(ZoneFileIssue(start_line, "Unbalanced opening parenthesis"))


def _expect(tokens: list[Token], count: int, record_type: RecordType) -> None:
    if len(tokens) != count:
        raise _LineError(
            f"{record_type} record data must have {count} field{'s' if count != 1 else ''}"
        )


def _absolute_target(text: str, origin: str) -> str:
    return "." if text == "." else to_absolute(text, origin)


def _quote(token: Token) -> str:
    return f'"{token.text}"'


def _rdata(record_type: RecordType, tokens: list[Token], origin: str) -> str:
    """Build a Route 53 style value from zone-file rdata tokens."""
    if not tokens:
        raise _LineError(f"{record_type} record has no data")
    texts = [token.text for token in tokens]
    match record_type:
        case RecordType.A | RecordType.AAAA:
            _expect(tokens, 1, record_type)
            return texts[0]
        case RecordType.CNAME | RecordType.NS | RecordType.PTR:
            _expect(tokens, 1, record_type)
            return _absolute_target(texts[0], origin)
        case RecordType.MX:
            _expect(tokens, 2, record_type)
            return f"{texts[0]} {_absolute_target(texts[1], origin)}"
        case RecordType.SRV:
            _expect(tokens, 4, record_type)
            return " ".join([*texts[:3], _absolute_target(texts[3], origin)])
        case RecordType.CAA:
            _expect(tokens, 3, record_type)
            return f"{texts[0]} {texts[1]} {_quote(tokens[2])}"
        case RecordType.TXT:
            return " ".join(_quote(token) for token in tokens)
        case RecordType.SOA:
            _expect(tokens, 7, record_type)
            timers = [str(parse_ttl(text)) for text in texts[2:]]
            return " ".join([to_absolute(texts[0], origin), to_absolute(texts[1], origin), *timers])


@dataclass(slots=True)
class _ParserState:
    zone_name: str
    origin: str
    default_ttl: int | None = None
    last_ttl: int | None = None
    last_owner: str | None = None


def _apply_directive(tokens: list[Token], state: _ParserState) -> None:
    directive = tokens[0].text.upper()
    if directive == "$ORIGIN":
        if len(tokens) != 2:
            raise _LineError("$ORIGIN requires exactly one domain name")
        state.origin = to_absolute(tokens[1].text, state.origin)
    elif directive == "$TTL":
        if len(tokens) != 2:
            raise _LineError("$TTL requires exactly one value")
        state.default_ttl = parse_ttl(tokens[1].text)
    else:
        raise _LineError(f"Directive {directive} is not supported")


def _parse_record(
    tokens: list[Token], starts_blank: bool, state: _ParserState
) -> tuple[str, RecordType, int, str]:
    remaining = list(tokens)
    if starts_blank:
        if state.last_owner is None:
            raise _LineError("Record has no owner name")
        owner = state.last_owner
    else:
        owner = to_absolute(remaining.pop(0).text, state.origin)
        state.last_owner = owner

    ttl: int | None = None
    while remaining and not remaining[0].quoted:
        head = remaining[0].text
        if head.upper() == _SUPPORTED_CLASS:
            remaining.pop(0)
        elif head.upper() in _OTHER_CLASSES:
            raise _LineError(f"Class {head.upper()} is not supported; only IN records are")
        elif ttl is None and _TTL_RE.match(head):
            ttl = parse_ttl(remaining.pop(0).text)
        else:
            break
    if not remaining:
        raise _LineError("Record is missing a type")

    type_text = remaining.pop(0).text.upper()
    try:
        record_type = RecordType(type_text)
    except ValueError:
        raise _LineError(f"Record type {type_text} is not supported") from None

    if ttl is None:
        ttl = state.default_ttl if state.default_ttl is not None else state.last_ttl
    if ttl is None:
        ttl = DEFAULT_TTL
    state.last_ttl = ttl

    try:
        name = normalize_record_name(owner, state.zone_name)
    except DnsNameError as exc:
        raise _LineError(str(exc)) from None
    return name, record_type, ttl, _rdata(record_type, remaining, state.origin)


def parse_zone_file(text: str, zone_name: str) -> ParsedZoneFile:
    """Parse a BIND zone file into record sets grouped by name and type.

    Problems are collected as issues with their line number instead of aborting, so the
    caller can show every error at once.
    """
    result = ParsedZoneFile()
    state = _ParserState(zone_name=zone_name, origin=zone_name)
    grouped: dict[tuple[str, RecordType], ParsedRecordSet] = {}

    for line, starts_blank, tokens in _logical_lines(text, result.issues):
        try:
            if not tokens[0].quoted and tokens[0].text.startswith("$"):
                _apply_directive(tokens, state)
                continue
            name, record_type, ttl, value = _parse_record(tokens, starts_blank, state)
            validate_values(record_type, [value])
        except (_LineError, RecordValueError) as exc:
            result.issues.append(ZoneFileIssue(line, str(exc)))
            continue

        record_set = grouped.get((name, record_type))
        if record_set is None:
            grouped[(name, record_type)] = ParsedRecordSet(name, record_type, ttl, [value], line)
        elif value not in record_set.values:
            record_set.values.append(value)

    result.record_sets = list(grouped.values())
    result.issues.sort(key=lambda issue: issue.line)
    return result


_TARGET_FIELD: dict[RecordType, tuple[int, ...]] = {
    RecordType.CNAME: (0,),
    RecordType.NS: (0,),
    RecordType.PTR: (0,),
    RecordType.MX: (1,),
    RecordType.SRV: (3,),
    RecordType.SOA: (0, 1),
}


def to_zone_file_value(record_type: RecordType, value: str) -> str:
    """Make host names inside a value absolute, as Route 53 always treats them as FQDNs."""
    positions = _TARGET_FIELD.get(record_type)
    if positions is None:
        return value
    fields = value.split()
    for position in positions:
        if position < len(fields) and not fields[position].endswith("."):
            fields[position] = f"{fields[position].lower()}."
    return " ".join(fields)


@dataclass(frozen=True, slots=True)
class ZoneFileRecord:
    name: str
    type: RecordType
    ttl: int
    values: tuple[str, ...]


def render_zone_file(
    zone_name: str, records: Iterable[ZoneFileRecord], comments: Iterable[str] = ()
) -> str:
    """Render record sets as a BIND zone file with fully qualified owner names."""
    lines = [f"; {comment}" for comment in comments]
    lines.append(f"$ORIGIN {zone_name}")
    for record in records:
        lines.extend(
            f"{record.name}\t{record.ttl}\tIN\t{record.type}\t"
            f"{to_zone_file_value(record.type, value)}"
            for value in record.values
        )
    return "\n".join(lines) + "\n"
