"use client";

import type { CollectionPreferencesProps } from "@cloudscape-design/components/collection-preferences";
import { useMemo } from "react";

import { usePersistedState } from "./use-persisted-state";

export type SearchMode = "automatic" | "full" | "fast";

export type TablePreferences = CollectionPreferencesProps.Preferences<SearchMode>;

export interface ColumnChoice {
  id: string;
  label: string;
  /** Hidden until the user turns it on in the preferences. */
  hiddenByDefault?: boolean;
  /** Cannot be hidden. */
  alwaysVisible?: boolean;
}

export const PAGE_SIZES = [10, 30, 50, 100];
const DEFAULT_PAGE_SIZE = 50;

/** Table preferences (page size, wrap lines, visible columns) remembered per table. */
export function useTablePreferences(tableId: string, columns: ColumnChoice[]) {
  const defaults = useMemo<TablePreferences>(
    () => ({
      pageSize: DEFAULT_PAGE_SIZE,
      wrapLines: false,
      custom: "automatic",
      contentDisplay: columns.map((column) => ({
        id: column.id,
        visible: !column.hiddenByDefault,
      })),
    }),
    [columns],
  );
  const [stored, setPreferences] = usePersistedState<TablePreferences>(
    `table.${tableId}`,
    defaults,
  );
  // Preferences saved by an older version may lack newer fields.
  const preferences = useMemo(() => ({ ...defaults, ...stored }), [defaults, stored]);
  return [preferences, setPreferences] as const;
}
