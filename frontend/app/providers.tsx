"use client";

import { I18nProvider } from "@cloudscape-design/components/i18n";
import messages from "@cloudscape-design/components/i18n/messages/all.en";
import { QueryClient, QueryClientProvider, useQueryClient } from "@tanstack/react-query";
import { usePathname, useRouter } from "next/navigation";
import { useEffect, useState } from "react";
import type { ReactNode } from "react";

import { useApplyVisualMode } from "@/hooks/use-visual-mode";
import { api } from "@/lib/api/client";
import { ApiError } from "@/lib/api/errors";
import { routes } from "@/lib/routes";

function createQueryClient() {
  return new QueryClient({
    defaultOptions: {
      queries: {
        staleTime: 30_000,
        refetchOnWindowFocus: false,
        // Client errors will not succeed on retry; only retry failures like a dropped connection.
        retry: (failureCount, error) =>
          failureCount < 2 && !(error instanceof ApiError && error.status < 500),
      },
    },
  });
}

/**
 * A 401 outside the sign-in page means the session expired. Clear the stale cookie (the
 * route guard would otherwise bounce the visitor straight back), drop cached data, then
 * return to sign-in and remember where they were.
 */
function SessionExpiryRedirect() {
  const router = useRouter();
  const pathname = usePathname();
  const queryClient = useQueryClient();

  useEffect(() => {
    if (pathname === routes.signIn) return;
    let handling = false;
    const onError = async (error: unknown) => {
      if (handling || !(error instanceof ApiError) || error.status !== 401) return;
      handling = true;
      await api.POST("/api/v1/auth/logout").catch(() => undefined);
      queryClient.clear();
      const destination = `${window.location.pathname}${window.location.search}`;
      router.replace(`${routes.signIn}?redirect=${encodeURIComponent(destination)}`);
    };
    const stopQueries = queryClient.getQueryCache().subscribe((event) => {
      if (event.type === "updated" && event.action.type === "error")
        void onError(event.action.error);
    });
    const stopMutations = queryClient.getMutationCache().subscribe((event) => {
      if (event.type === "updated" && event.action.type === "error")
        void onError(event.action.error);
    });
    return () => {
      stopQueries();
      stopMutations();
    };
  }, [pathname, queryClient, router]);

  return null;
}

export function Providers({ children }: { children: ReactNode }) {
  const [queryClient] = useState(createQueryClient);
  useApplyVisualMode();
  return (
    <QueryClientProvider client={queryClient}>
      <I18nProvider locale="en" messages={[messages]}>
        <SessionExpiryRedirect />
        {children}
      </I18nProvider>
    </QueryClientProvider>
  );
}
