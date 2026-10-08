"use client";

import CollectionPreferences from "@cloudscape-design/components/collection-preferences";
import FormField from "@cloudscape-design/components/form-field";
import RadioGroup from "@cloudscape-design/components/radio-group";

import { PAGE_SIZES } from "@/hooks/use-table-preferences";
import type { ColumnChoice, SearchMode, TablePreferences } from "@/hooks/use-table-preferences";

interface TablePreferencesButtonProps {
  columns: ColumnChoice[];
  preferences: TablePreferences;
  onConfirm: (preferences: TablePreferences) => void;
}

/** The gear button above a table and its Preferences dialog, as in the console. */
export function TablePreferencesButton({
  columns,
  preferences,
  onConfirm,
}: TablePreferencesButtonProps) {
  return (
    <CollectionPreferences
      title="Preferences"
      confirmLabel="Confirm"
      cancelLabel="Cancel"
      preferences={preferences}
      onConfirm={({ detail }) => onConfirm(detail)}
      pageSizePreference={{
        title: "Page size",
        options: PAGE_SIZES.map((value) => ({ value, label: `${value} items` })),
      }}
      wrapLinesPreference={{
        label: "Wrap lines",
        description: "Check to see all the text and wrap the lines.",
      }}
      customPreference={(value, setValue) => (
        <FormField label="Search mode">
          <RadioGroup
            value={value ?? "automatic"}
            onChange={({ detail }) => setValue(detail.value as SearchMode)}
            items={[
              {
                value: "automatic",
                label: "Automatic",
                description:
                  "The service chooses a filter mode based on the total number of items.",
              },
              {
                value: "full",
                label: "Full",
                description:
                  "All search filters are available, but search performance might be slower.",
              },
              {
                value: "fast",
                label: "Fast",
                description:
                  "Some advanced searches may not be available, but search performance will be faster.",
              },
            ]}
          />
        </FormField>
      )}
      contentDisplayPreference={{
        title: "Select visible columns",
        options: columns.map(({ id, label, alwaysVisible }) => ({ id, label, alwaysVisible })),
      }}
    />
  );
}
