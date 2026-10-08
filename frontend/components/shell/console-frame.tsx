"use client";

import { useState } from "react";
import type { ReactNode } from "react";

import { useShortcutListener } from "@/hooks/use-shortcuts";

import { GlobalFooter } from "./global-footer";
import { GlobalHeader } from "./global-header";
import { NotificationsProvider } from "./notifications";
import { ShortcutsModal } from "./shortcuts-modal";

/** Everything that stays in place while moving between console pages. */
export function ConsoleFrame({ children }: { children: ReactNode }) {
  const [shortcutsVisible, setShortcutsVisible] = useState(false);
  useShortcutListener(() => setShortcutsVisible(true));

  return (
    <NotificationsProvider>
      <GlobalHeader />
      {children}
      <GlobalFooter onShowShortcuts={() => setShortcutsVisible(true)} />
      {shortcutsVisible && <ShortcutsModal onDismiss={() => setShortcutsVisible(false)} />}
    </NotificationsProvider>
  );
}
