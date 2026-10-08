"use client";

import { useRouter } from "next/navigation";
import { useCallback } from "react";

interface FollowDetail {
  href?: string;
  external?: boolean;
  target?: string;
}

/**
 * Handler for the `onFollow` event of Cloudscape links, buttons, breadcrumbs and
 * navigation: internal links go through the Next.js router instead of reloading the page.
 */
export function useFollow() {
  const router = useRouter();
  return useCallback(
    (event: CustomEvent<FollowDetail>) => {
      const { href, external, target } = event.detail;
      if (!href || external || target === "_blank" || !href.startsWith("/")) return;
      event.preventDefault();
      router.push(href);
    },
    [router],
  );
}
