"use client";

import Box from "@cloudscape-design/components/box";
import Button from "@cloudscape-design/components/button";
import type { FlashbarProps } from "@cloudscape-design/components/flashbar";
import { createContext, useCallback, useContext, useMemo, useState } from "react";
import type { ReactNode } from "react";

import { ApiError } from "@/lib/api/errors";
import { errorDetail } from "@/lib/format";

interface Notifier {
  /** Green flash: a zone was created or deleted, records were deleted. */
  success: (header: string, content?: ReactNode) => void;
  /** Blue flash the console shows after record changes, with the propagation note. */
  recordsChanged: (header: string) => void;
  /** Plain blue flash, for actions that are outside the clone's scope. */
  info: (header: string, content?: ReactNode) => void;
  /** Red "Error occurred" flash with the service's detail in parentheses. */
  error: (error: unknown) => void;
  /**
   * Blue flash with a spinner, shown while a zone or its records are being created.
   * Returns the function that removes it once the request has settled.
   */
  progress: (header: string) => () => void;
}

interface NotificationsValue {
  items: FlashbarProps.MessageDefinition[];
  notify: Notifier;
}

const NotificationsContext = createContext<NotificationsValue | null>(null);

const PROPAGATION_NOTE =
  'Route 53 propagates your changes to all of the Route 53 authoritative DNS servers within 60 seconds. Use "View status" button to check propagation status.';

function describeError(error: unknown): string {
  if (error instanceof ApiError) return errorDetail(error.message);
  return error instanceof Error ? error.message : "The request could not be completed.";
}

export function NotificationsProvider({ children }: { children: ReactNode }) {
  const [items, setItems] = useState<FlashbarProps.MessageDefinition[]>([]);

  const dismiss = useCallback((id: string) => {
    setItems((current) => current.filter((item) => item.id !== id));
  }, []);

  const push = useCallback(
    (
      item: Omit<FlashbarProps.MessageDefinition, "id" | "dismissible" | "onDismiss">,
      // A completed change answers the errors that came before it, so they leave the stack.
      { resolvesErrors = false } = {},
    ) => {
      const id = crypto.randomUUID();
      setItems((current) => [
        {
          ...item,
          id,
          dismissible: true,
          dismissLabel: "Dismiss notification",
          onDismiss: () => dismiss(id),
        },
        ...(resolvesErrors ? current.filter((earlier) => earlier.type !== "error") : current),
      ]);
      return id;
    },
    [dismiss],
  );

  const notify = useMemo<Notifier>(
    () => ({
      success: (header, content) =>
        push({ type: "success", header, content }, { resolvesErrors: true }),
      recordsChanged: (header) =>
        push(
          {
            type: "info",
            header,
            content: PROPAGATION_NOTE,
            action: (
              <Button
                onClick={() =>
                  push({
                    type: "success",
                    header: "Status: INSYNC",
                    content: "Your changes have propagated to all Route 53 DNS servers.",
                  })
                }
              >
                View status
              </Button>
            ),
          },
          { resolvesErrors: true },
        ),
      info: (header, content) => push({ type: "info", header, content }),
      progress: (header) => {
        const id = push({
          type: "info",
          loading: true,
          header,
          content: "This can take a moment.",
        });
        return () => dismiss(id);
      },
      error: (error) =>
        push({
          type: "error",
          header: "Error occurred",
          content: (
            <>
              Please try again later.
              <br />
              <Box variant="code" color="inherit" fontSize="body-m">
                ({describeError(error)})
              </Box>
            </>
          ),
        }),
    }),
    [push, dismiss],
  );

  const value = useMemo(() => ({ items, notify }), [items, notify]);
  return <NotificationsContext.Provider value={value}>{children}</NotificationsContext.Provider>;
}

function useNotificationsContext(): NotificationsValue {
  const value = useContext(NotificationsContext);
  if (!value) throw new Error("useNotifications must be used inside NotificationsProvider");
  return value;
}

export function useNotify(): Notifier {
  return useNotificationsContext().notify;
}

export function useNotificationItems(): FlashbarProps.MessageDefinition[] {
  return useNotificationsContext().items;
}
