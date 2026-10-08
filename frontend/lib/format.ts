import type { RoutingPolicy, ZoneType } from "@/lib/api/types";

const numberFormat = new Intl.NumberFormat("en-US");

/** Names are stored with a trailing dot; the console shows them without it. */
export function displayName(name: string): string {
  return name.replace(/\.$/, "");
}

/** The part of a record name before the zone name, as typed in the "Record name" field. */
export function subdomainOf(recordName: string, zoneName: string): string {
  if (recordName === zoneName) return "";
  return recordName.endsWith(`.${zoneName}`)
    ? recordName.slice(0, -zoneName.length - 1)
    : displayName(recordName);
}

export function formatNumber(value: number): string {
  return numberFormat.format(value);
}

/** Placeholder the console shows for an empty cell. */
export const EMPTY = "-";

export function orDash(value: string | number | null | undefined): string {
  return value === null || value === undefined || value === "" ? EMPTY : String(value);
}

export const zoneTypeLabel: Record<ZoneType, string> = { public: "Public", private: "Private" };

export const zoneTypeLongLabel: Record<ZoneType, string> = {
  public: "Public hosted zone",
  private: "Private hosted zone",
};

export const routingPolicyLabel: Record<RoutingPolicy, string> = {
  simple: "Simple",
  weighted: "Weighted",
  latency: "Latency",
  failover: "Failover",
  geolocation: "Geolocation",
  multivalue: "Multivalue answer",
};

const RECORD_ERROR_PREFIX = "Invalid Resource Record: 'FATAL problem: ";

/**
 * Route 53 wraps record rejections as `Invalid Resource Record: 'FATAL problem: <detail>'`.
 * The console shows the detail, including the wrapper's closing quote.
 */
export function errorDetail(message: string): string {
  return message.startsWith(RECORD_ERROR_PREFIX)
    ? message.slice(RECORD_ERROR_PREFIX.length)
    : message;
}
