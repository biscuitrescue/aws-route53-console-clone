"use client";

import { useCallback, useMemo, useSyncExternalStore } from "react";

const PREFIX = "r53clone.";
const listeners = new Set<() => void>();

function subscribe(listener: () => void) {
  listeners.add(listener);
  window.addEventListener("storage", listener);
  return () => {
    listeners.delete(listener);
    window.removeEventListener("storage", listener);
  };
}

function read(key: string): string | null {
  try {
    return window.localStorage.getItem(PREFIX + key);
  } catch {
    return null;
  }
}

/** Read a persisted value once, outside React; `fallback` when it is missing or unreadable. */
export function readPersisted<Value>(key: string, fallback: Value): Value {
  const raw = typeof window === "undefined" ? null : read(key);
  if (raw === null) return fallback;
  try {
    return JSON.parse(raw) as Value;
  } catch {
    return fallback;
  }
}

/**
 * State kept in localStorage, shared by every component using the same key and synced
 * across tabs. The server and the first client render use `fallback`.
 */
export function usePersistedState<Value>(key: string, fallback: Value) {
  const raw = useSyncExternalStore(
    subscribe,
    () => read(key),
    () => null,
  );

  const value = useMemo<Value>(() => {
    if (raw === null) return fallback;
    try {
      return JSON.parse(raw) as Value;
    } catch {
      return fallback;
    }
  }, [raw, fallback]);

  const setValue = useCallback(
    (next: Value) => {
      try {
        window.localStorage.setItem(PREFIX + key, JSON.stringify(next));
      } catch {
        // Storage can be unavailable (private mode, quota); the value then lasts for this render only.
      }
      listeners.forEach((listener) => listener());
    },
    [key],
  );

  return [value, setValue] as const;
}
