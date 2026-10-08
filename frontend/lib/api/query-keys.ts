import type { RecordListParams, ZoneListParams } from "./params";

/** Cache keys, nested so a whole zone or list can be invalidated with one prefix. */
export const queryKeys = {
  session: ["session"] as const,
  zones: ["zones"] as const,
  zoneLists: ["zones", "list"] as const,
  zoneList: (params: ZoneListParams) => ["zones", "list", params] as const,
  zone: (zoneId: string) => ["zones", "detail", zoneId] as const,
  records: (zoneId: string) => ["zones", "detail", zoneId, "records"] as const,
  recordList: (zoneId: string, params: RecordListParams) =>
    ["zones", "detail", zoneId, "records", params] as const,
};
