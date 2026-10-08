"use client";

import { keepPreviousData, useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import { api, unwrap } from "@/lib/api/client";
import { toListQuery } from "@/lib/api/params";
import type { RecordListParams } from "@/lib/api/params";
import { queryKeys } from "@/lib/api/query-keys";
import type { Change, RecordSetInput, RecordSetUpdate } from "@/lib/api/types";

export function useRecords(zoneId: string, params: RecordListParams) {
  return useQuery({
    queryKey: queryKeys.recordList(zoneId, params),
    queryFn: () =>
      unwrap(
        api.GET("/api/v1/hostedzones/{zone_id}/records", {
          params: {
            path: { zone_id: zoneId },
            query: { ...toListQuery(params), type: params.types },
          },
        }),
      ),
    placeholderData: keepPreviousData,
  });
}

/**
 * Every record mutation changes the zone's record list and its record count, so they
 * all refresh the zone (which covers its records) and the zone lists.
 */
function useInvalidateZone(zoneId: string) {
  const queryClient = useQueryClient();
  return () =>
    Promise.all([
      queryClient.invalidateQueries({ queryKey: queryKeys.zone(zoneId) }),
      queryClient.invalidateQueries({ queryKey: queryKeys.zoneLists }),
    ]);
}

export function useCreateRecord(zoneId: string) {
  return useMutation({
    mutationFn: (record: RecordSetInput) =>
      unwrap(
        api.POST("/api/v1/hostedzones/{zone_id}/records", {
          params: { path: { zone_id: zoneId } },
          body: record,
        }),
      ),
    onSuccess: useInvalidateZone(zoneId),
  });
}

export function useUpdateRecord(zoneId: string) {
  return useMutation({
    mutationFn: ({ recordId, changes }: { recordId: string; changes: RecordSetUpdate }) =>
      unwrap(
        api.PATCH("/api/v1/hostedzones/{zone_id}/records/{record_id}", {
          params: { path: { zone_id: zoneId, record_id: recordId } },
          body: changes,
        }),
      ),
    onSuccess: useInvalidateZone(zoneId),
  });
}

/** Apply several changes atomically: bulk create, edit and delete go through here. */
export function useChangeRecords(zoneId: string) {
  return useMutation({
    mutationFn: (changes: Change[]) =>
      unwrap(
        api.POST("/api/v1/hostedzones/{zone_id}/records:batch", {
          params: { path: { zone_id: zoneId } },
          body: { changes },
        }),
      ),
    onSuccess: useInvalidateZone(zoneId),
  });
}

export function useImportZoneFile(zoneId: string) {
  const invalidate = useInvalidateZone(zoneId);
  return useMutation({
    mutationFn: (request: { content: string; dryRun: boolean; replaceExisting: boolean }) =>
      unwrap(
        api.POST("/api/v1/hostedzones/{zone_id}/import", {
          params: { path: { zone_id: zoneId } },
          body: {
            content: request.content,
            dry_run: request.dryRun,
            replace_existing: request.replaceExisting,
          },
        }),
      ),
    onSuccess: (result) => (result.applied ? invalidate() : undefined),
  });
}
