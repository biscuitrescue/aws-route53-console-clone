"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import { api, unwrap } from "@/lib/api/client";
import { queryKeys } from "@/lib/api/query-keys";

/** The signed-in user. Fails with a 401 `ApiError` when the session is missing or expired. */
export function useSession() {
  return useQuery({
    queryKey: queryKeys.session,
    queryFn: () => unwrap(api.GET("/api/v1/auth/me")),
    staleTime: 5 * 60_000,
  });
}

export function useSignIn() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (credentials: { email: string; password: string }) =>
      unwrap(api.POST("/api/v1/auth/login", { body: credentials })),
    onSuccess: (session) => queryClient.setQueryData(queryKeys.session, session),
  });
}

export function useSignOut() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: () => unwrap(api.POST("/api/v1/auth/logout")),
    // Drop every cached response so nothing from this account outlives the session.
    onSuccess: () => queryClient.clear(),
  });
}
