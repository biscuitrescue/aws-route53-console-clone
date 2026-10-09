import type {
  ChangeBatchResult,
  RecordSet,
  RecordSetInput,
  RecordType,
  RoutingPolicy,
} from "@/lib/api/types";
import { DEFAULT_TTL } from "@/lib/record-types";

import { endpointForTarget } from "./alias-endpoints";
import { displayName, subdomainOf } from "./format";

/** The editable state of one record form. Everything is text, as the user typed it. */
export interface RecordDraft {
  /** Stable React key for lists of record forms. */
  key: string;
  name: string;
  type: RecordType;
  alias: boolean;
  /** One value per line. */
  values: string;
  ttl: string;
  /** Kind of alias target chosen under "Route traffic to"; a key of `aliasEndpoints`. */
  aliasEndpoint: string;
  /** Region of the alias target. Kept in the form only: the API has no use for it. */
  aliasRegion: string;
  aliasDnsName: string;
  aliasHostedZoneId: string;
  evaluateTargetHealth: boolean;
  routingPolicy: RoutingPolicy;
  setIdentifier: string;
  weight: string;
  region: string;
  failover: "" | "PRIMARY" | "SECONDARY";
  continentCode: string;
  countryCode: string;
}

export type RecordField =
  | "name"
  | "values"
  | "ttl"
  | "alias"
  | "setIdentifier"
  | "weight"
  | "region"
  | "failover"
  | "location";

export type RecordErrors = Partial<Record<RecordField, string>>;

export function emptyDraft(): RecordDraft {
  return {
    key: crypto.randomUUID(),
    name: "",
    type: "A",
    alias: false,
    values: "",
    ttl: String(DEFAULT_TTL),
    aliasEndpoint: "",
    aliasRegion: "",
    aliasDnsName: "",
    aliasHostedZoneId: "",
    evaluateTargetHealth: false,
    routingPolicy: "simple",
    setIdentifier: "",
    weight: "",
    region: "",
    failover: "",
    continentCode: "",
    countryCode: "",
  };
}

export function draftFromRecord(record: RecordSet, zoneName: string): RecordDraft {
  return {
    key: record.id,
    name: subdomainOf(record.name, zoneName),
    type: record.type,
    alias: record.alias,
    values: record.values.join("\n"),
    ttl: record.ttl === null ? String(DEFAULT_TTL) : String(record.ttl),
    aliasEndpoint: record.alias_target
      ? endpointForTarget(record.alias_target.hosted_zone_id, record.zone_id)
      : "",
    aliasRegion: "",
    aliasDnsName: record.alias_target ? displayName(record.alias_target.dns_name) : "",
    aliasHostedZoneId: record.alias_target?.hosted_zone_id ?? "",
    evaluateTargetHealth: record.alias_target?.evaluate_target_health ?? false,
    routingPolicy: record.routing_policy,
    setIdentifier: record.set_identifier ?? "",
    weight: record.weight === null ? "" : String(record.weight),
    region: record.region ?? "",
    failover: record.failover ?? "",
    continentCode: record.geolocation?.continent_code ?? "",
    countryCode: record.geolocation?.country_code ?? "",
  };
}

function splitValues(text: string): string[] {
  return text
    .split("\n")
    .map((line) => line.trim())
    .filter(Boolean);
}

/**
 * Checks that can be made without the server, mirroring what the console validates inline.
 * Everything else (value formats, conflicts) is reported by the API.
 */
export function validateDraft(draft: RecordDraft): RecordErrors {
  const errors: RecordErrors = {};
  if (draft.alias) {
    if (!draft.aliasDnsName.trim() || !draft.aliasHostedZoneId.trim()) {
      errors.alias = "Endpoints field is required to have value.";
    }
  } else {
    if (splitValues(draft.values).length === 0)
      errors.values = "Endpoints field is required to have value.";
    if (!/^\d+$/.test(draft.ttl.trim())) errors.ttl = "TTL must be a whole number of seconds.";
  }
  if (draft.routingPolicy !== "simple") {
    if (!draft.setIdentifier.trim())
      errors.setIdentifier = "Record ID is required for this routing policy.";
    if (draft.routingPolicy === "weighted" && !/^\d+$/.test(draft.weight.trim())) {
      errors.weight = "Weight must be a whole number between 0 and 255.";
    }
    if (draft.routingPolicy === "latency" && !draft.region) errors.region = "Choose a Region.";
    if (draft.routingPolicy === "failover" && !draft.failover)
      errors.failover = "Choose a failover record type.";
    if (
      draft.routingPolicy === "geolocation" &&
      !draft.continentCode &&
      !draft.countryCode.trim()
    ) {
      errors.location = "Choose a location.";
    }
  }
  return errors;
}

export function hasErrors(errors: RecordErrors): boolean {
  return Object.keys(errors).length > 0;
}

/** The API payload for a draft. Call only after `validateDraft` found no errors. */
export function draftToInput(draft: RecordDraft): RecordSetInput {
  const routed = draft.routingPolicy !== "simple";
  return {
    name: draft.name.trim(),
    type: draft.type,
    ttl: draft.alias ? null : Number(draft.ttl),
    values: draft.alias ? [] : splitValues(draft.values),
    alias_target: draft.alias
      ? {
          dns_name: draft.aliasDnsName.trim(),
          hosted_zone_id: draft.aliasHostedZoneId.trim(),
          evaluate_target_health: draft.evaluateTargetHealth,
        }
      : null,
    routing_policy: draft.routingPolicy,
    set_identifier: routed ? draft.setIdentifier.trim() : null,
    weight: draft.routingPolicy === "weighted" ? Number(draft.weight) : null,
    region: draft.routingPolicy === "latency" ? draft.region : null,
    failover: draft.routingPolicy === "failover" && draft.failover ? draft.failover : null,
    geolocation:
      draft.routingPolicy === "geolocation"
        ? {
            continent_code: draft.continentCode || null,
            country_code: draft.continentCode
              ? null
              : draft.countryCode.trim().toUpperCase() || null,
          }
        : null,
  };
}

/** The flash header after creating records: one is named, several are counted by zone. */
export function createdRecordsHeader(result: ChangeBatchResult, zoneName: string): string {
  const [first] = result.record_sets;
  return result.created === 1 && first
    ? `${displayName(first.name)} was successfully created.`
    : `Records for ${zoneName} were successfully created.`;
}

/** The identifying part of a record, enough for a DELETE change. */
export function recordIdentity(record: RecordSet): RecordSetInput {
  return { name: record.name, type: record.type, set_identifier: record.set_identifier };
}

/** What the "Differentiator" column shows: the value that tells same-named records apart. */
export function differentiator(record: RecordSet): string | null {
  switch (record.routing_policy) {
    case "weighted":
      return record.weight === null ? null : String(record.weight);
    case "latency":
      return record.region;
    case "failover":
      return record.failover === "PRIMARY"
        ? "Primary"
        : record.failover === "SECONDARY"
          ? "Secondary"
          : null;
    case "geolocation":
      return record.geolocation?.country_code ?? record.geolocation?.continent_code ?? null;
    default:
      return null;
  }
}

/** What a record routes to: its values, or its alias target. */
export function recordTargets(record: RecordSet): string[] {
  return record.alias && record.alias_target ? [record.alias_target.dns_name] : record.values;
}
