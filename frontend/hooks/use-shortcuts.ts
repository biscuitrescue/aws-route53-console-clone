"use client";

import { useEffect, useRef, useSyncExternalStore } from "react";

export interface Shortcut {
  /** `KeyboardEvent.key` of an unmodified key press, for example "c" or "/". */
  key: string;
  description: string;
}

interface RegisteredShortcut extends Shortcut {
  run: () => void;
}

// Shortcuts belong to whichever page is on screen, so they live in one small store
// rather than in React state: registering one must not re-render the page.
const registry = new Map<string, RegisteredShortcut>();
const listeners = new Set<() => void>();
let snapshot: Shortcut[] = [];

function publish() {
  snapshot = [...registry.values()].map(({ key, description }) => ({ key, description }));
  listeners.forEach((listener) => listener());
}

function subscribe(listener: () => void) {
  listeners.add(listener);
  return () => {
    listeners.delete(listener);
  };
}

const EMPTY: Shortcut[] = [];

/** Register a single-key shortcut for as long as the calling component is mounted. */
export function useShortcut(key: string, description: string, action: () => void, enabled = true) {
  const latest = useRef(action);
  useEffect(() => {
    latest.current = action;
  });

  useEffect(() => {
    if (!enabled) return;
    registry.set(key, { key, description, run: () => latest.current() });
    publish();
    return () => {
      registry.delete(key);
      publish();
    };
  }, [key, description, enabled]);
}

/** The shortcuts registered by the current page, for the help dialog. */
export function useRegisteredShortcuts(): Shortcut[] {
  return useSyncExternalStore(
    subscribe,
    () => snapshot,
    () => EMPTY,
  );
}

function isTyping(target: EventTarget | null): boolean {
  if (!(target instanceof HTMLElement)) return false;
  return target.isContentEditable || ["INPUT", "TEXTAREA", "SELECT"].includes(target.tagName);
}

/**
 * Listen for shortcut keys on the whole document. Keys are ignored while the user is
 * typing, while a dialog is open, and when a modifier is held, so they never clash with
 * the browser or with form input.
 */
export function useShortcutListener(onHelp: () => void) {
  const latestHelp = useRef(onHelp);
  useEffect(() => {
    latestHelp.current = onHelp;
  });

  useEffect(() => {
    const onKeyDown = (event: KeyboardEvent) => {
      if (event.ctrlKey || event.metaKey || event.altKey || isTyping(event.target)) return;
      if (document.querySelector('[role="dialog"][aria-modal="true"]:not([hidden])')) return;
      if (event.key === "?") {
        event.preventDefault();
        latestHelp.current();
        return;
      }
      const shortcut = registry.get(event.key);
      if (shortcut) {
        event.preventDefault();
        shortcut.run();
      }
    };
    document.addEventListener("keydown", onKeyDown);
    return () => document.removeEventListener("keydown", onKeyDown);
  }, []);
}
