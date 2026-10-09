"use client";

import Box from "@cloudscape-design/components/box";
import Button from "@cloudscape-design/components/button";
import type { FlashbarProps } from "@cloudscape-design/components/flashbar";
import { createContext, useCallback, useContext, useEffect, useMemo, useState } from "react";
import type { ReactNode } from "react";

import { useChangeStatus } from "@/hooks/use-records";
import { ApiError } from "@/lib/api/errors";
import { errorDetail } from "@/lib/format";

interface Notifier {
  /** Green flash: a zone was created or deleted, records were deleted. */
  success: (header: string, content?: ReactNode) => void;
  /**
   * Blue flash the console shows after record changes, with the propagation note. Its
   * "View status" button reports the status of the change with the given ID.
   */
  recordsChanged: (header: string, changeId?: string | null) => void;
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

/** The flash that reports a change's status; there is one per change. */
const statusFlashId = (changeId: string) => `change-status-${changeId}`;

const timeOfDay = new Intl.DateTimeFormat(undefined, { timeStyle: "medium" });

type FlashUpdate = Omit<FlashbarProps.MessageDefinition, "id" | "dismissible" | "onDismiss">;

/**
 * Follows one change from PENDING to INSYNC and keeps its flash up to date. Renders
 * nothing; it exists so that each watched change gets its own polling query.
 */
function ChangeStatusWatcher({
  changeId,
  onUpdate,
}: {
  changeId: string;
  onUpdate: (changeId: string, update: FlashUpdate) => void;
}) {
  const { data, isError } = useChangeStatus(changeId);
  useEffect(() => {
    if (data) {
      const pending = data.status === "PENDING";
      onUpdate(changeId, {
        type: pending ? "info" : "success",
        loading: pending,
        header: `Status: ${data.status}`,
        content: `Change ${data.id}, submitted at ${timeOfDay.format(new Date(data.submitted_at))}.`,
      });
    } else if (isError) {
      onUpdate(changeId, {
        type: "error",
        loading: false,
        header: "Status unavailable",
        content: `The status of change ${changeId} could not be retrieved.`,
      });
    }
  }, [changeId, data, isError, onUpdate]);
  return null;
}

function describeError(error: unknown): string {
  if (error instanceof ApiError) return errorDetail(error.message);
  return error instanceof Error ? error.message : "The request could not be completed.";
}

export function NotificationsProvider({ children }: { children: ReactNode }) {
  const [items, setItems] = useState<FlashbarProps.MessageDefinition[]>([]);
  // Changes whose status flash is showing; each is polled until it is INSYNC.
  const [watched, setWatched] = useState<string[]>([]);

  const dismiss = useCallback((id: string) => {
    setItems((current) => current.filter((item) => item.id !== id));
    setWatched((current) => current.filter((changeId) => statusFlashId(changeId) !== id));
  }, []);

  /** Show the status flash of a change, or bring it back to the top if it is showing. */
  const viewStatus = useCallback(
    (changeId: string) => {
      const id = statusFlashId(changeId);
      setItems((current) => [
        current.find((item) => item.id === id) ?? {
          id,
          type: "info",
          loading: true,
          header: "Checking status",
          content: `Change ${changeId}`,
          dismissible: true,
          dismissLabel: "Dismiss notification",
          onDismiss: () => dismiss(id),
        },
        ...current.filter((item) => item.id !== id),
      ]);
      setWatched((current) => (current.includes(changeId) ? current : [...current, changeId]));
    },
    [dismiss],
  );

  const updateStatus = useCallback((changeId: string, update: FlashUpdate) => {
    const id = statusFlashId(changeId);
    setItems((current) => current.map((item) => (item.id === id ? { ...item, ...update } : item)));
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
      recordsChanged: (header, changeId) =>
        push(
          {
            type: "info",
            header,
            content: PROPAGATION_NOTE,
            action: changeId ? (
              <Button onClick={() => viewStatus(changeId)}>View status</Button>
            ) : undefined,
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
    [push, dismiss, viewStatus],
  );

  const value = useMemo(() => ({ items, notify }), [items, notify]);
  return (
    <NotificationsContext.Provider value={value}>
      {watched.map((changeId) => (
        <ChangeStatusWatcher key={changeId} changeId={changeId} onUpdate={updateStatus} />
      ))}
      {children}
    </NotificationsContext.Provider>
  );
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
