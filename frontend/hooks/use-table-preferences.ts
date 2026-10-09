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
}

export const PAGE_SIZES = [10, 30, 50, 100];
const DEFAULT_PAGE_SIZE = 100;

/** Table preferences (page size, wrap lines, visible columns) remembered per table. */
export function useTablePreferences(tableId: string, columns: ColumnChoice[]) {
  const defaults = useMemo<TablePreferences>(
    () => ({
      pageSize: DEFAULT_PAGE_SIZE,
      wrapLines: false,
      visibleContent: columns.filter((column) => !column.hiddenByDefault).map(({ id }) => id),
    }),
    [columns],
  );
  const [stored, setPreferences] = usePersistedState<TablePreferences>(
    `table.${tableId}`,
    defaults,
  );
  // Preferences saved by an older version may lack newer fields.
  const preferences = useMemo(
    () => ({
      ...defaults,
      ...stored,
      visibleContent: stored.visibleContent ?? defaults.visibleContent,
    }),
    [defaults, stored],
  );
  return [preferences, setPreferences] as const;
}
