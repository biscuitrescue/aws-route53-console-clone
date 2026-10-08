/** URL paths of the app. They follow the Route 53 console's sections and names. */
const HOSTED_ZONES = "/route53/v2/hostedzones";

export const routes = {
  signIn: "/signin",
  dashboard: "/route53/v2/home",
  hostedZones: HOSTED_ZONES,
  createHostedZone: `${HOSTED_ZONES}/create`,
  hostedZone: (zoneId: string) => `${HOSTED_ZONES}/${zoneId}`,
  editHostedZone: (zoneId: string) => `${HOSTED_ZONES}/${zoneId}/edit`,
  createRecord: (zoneId: string) => `${HOSTED_ZONES}/${zoneId}/records/create`,
  importZoneFile: (zoneId: string) => `${HOSTED_ZONES}/${zoneId}/records/import`,
} as const;

/** Name of the httpOnly session cookie set by the backend (R53_SESSION_COOKIE_NAME). */
export const SESSION_COOKIE = "r53_session";

/**
 * The real console addresses its pages with hash fragments such as
 * `#ListRecordSets/Z123`. Translate one into this app's path so pasted console-style
 * links still work. Returns `null` for an unknown or empty fragment.
 */
export function pathForConsoleHash(hash: string): string | null {
  const [name, zoneId] = hash.replace(/^#\/?/, "").split("/");
  if (name === "CreateHostedZone") return routes.createHostedZone;
  if (!zoneId) return null;
  switch (name) {
    case "ListRecordSets":
      return routes.hostedZone(zoneId);
    case "EditHostedZone":
      return routes.editHostedZone(zoneId);
    case "CreateRecordSet":
      return routes.createRecord(zoneId);
    case "ImportZoneFileRecordSets":
      return routes.importZoneFile(zoneId);
    default:
      return null;
  }
}
