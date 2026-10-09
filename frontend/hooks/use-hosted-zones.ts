"use client";

import {
  keepPreviousData,
  queryOptions,
  useMutation,
  useQuery,
  useQueryClient,
} from "@tanstack/react-query";

import { api, unwrap } from "@/lib/api/client";
import { toListQuery } from "@/lib/api/params";
import type { ZoneListParams } from "@/lib/api/params";
import { queryKeys } from "@/lib/api/query-keys";
import type { HostedZoneCreate, HostedZoneUpdate } from "@/lib/api/types";

/** One page of the zone list. Shared with the code that requests it ahead of the page. */
export function zoneListOptions(params: ZoneListParams) {
  return queryOptions({
    queryKey: queryKeys.zoneList(params),
    queryFn: () =>
      unwrap(
        api.GET("/api/v1/hostedzones", {
          params: { query: { ...toListQuery(params), type: params.type } },
        }),
      ),
  });
}

export function useHostedZones(params: ZoneListParams, options: { enabled?: boolean } = {}) {
  return useQuery({
    ...zoneListOptions(params),
    // Keep the current rows on screen while the next page or filter loads.
    placeholderData: keepPreviousData,
    enabled: options.enabled ?? true,
  });
}

export function zoneOptions(zoneId: string) {
  return queryOptions({
    queryKey: queryKeys.zone(zoneId),
    queryFn: () =>
      unwrap(api.GET("/api/v1/hostedzones/{zone_id}", { params: { path: { zone_id: zoneId } } })),
  });
}

export function useHostedZone(zoneId: string, options: { enabled?: boolean } = {}) {
  return useQuery({ ...zoneOptions(zoneId), enabled: options.enabled ?? true });
}

export function useCreateHostedZone() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (zone: HostedZoneCreate) => unwrap(api.POST("/api/v1/hostedzones", { body: zone })),
    onSuccess: (zone) => {
      queryClient.setQueryData(queryKeys.zone(zone.id), zone);
      return queryClient.invalidateQueries({ queryKey: queryKeys.zones });
    },
  });
}

export function useUpdateHostedZone(zoneId: string) {
  const queryClient = useQueryClient();
  return useMutation({
    // Description, tags and VPC associations are saved together, or not at all.
    mutationFn: (changes: HostedZoneUpdate) =>
      unwrap(
        api.PATCH("/api/v1/hostedzones/{zone_id}", {
          params: { path: { zone_id: zoneId } },
          body: changes,
        }),
      ),
    onSuccess: (zone) => {
      queryClient.setQueryData(queryKeys.zone(zoneId), zone);
      return queryClient.invalidateQueries({ queryKey: queryKeys.zoneLists });
    },
  });
}

export function useDeleteHostedZone() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (zoneId: string) =>
      unwrap(
        api.DELETE("/api/v1/hostedzones/{zone_id}", { params: { path: { zone_id: zoneId } } }),
      ),
    onSuccess: (_result, zoneId) => {
      queryClient.removeQueries({ queryKey: queryKeys.zone(zoneId) });
      return queryClient.invalidateQueries({ queryKey: queryKeys.zones });
    },
  });
}
