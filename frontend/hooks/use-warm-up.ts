"use client";

import { useEffect } from "react";

/**
 * Download the code of the page the visitor is most likely to open next, once the current
 * page is idle. Navigating there then needs no script requests, which matters on a slow or
 * distant connection. `load` must be a stable function, typically one made of `import()`s.
 */
export function useWarmUp(load: () => Promise<unknown>) {
  useEffect(() => {
    const run = () => void load().catch(() => undefined);
    if (typeof window.requestIdleCallback === "function") {
      const handle = window.requestIdleCallback(run, { timeout: 2000 });
      return () => window.cancelIdleCallback(handle);
    }
    const handle = window.setTimeout(run, 200);
    return () => window.clearTimeout(handle);
  }, [load]);
}
