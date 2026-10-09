"use client";

import Box from "@cloudscape-design/components/box";
import Button from "@cloudscape-design/components/button";
import Header from "@cloudscape-design/components/header";
import Pagination from "@cloudscape-design/components/pagination";
import PropertyFilter from "@cloudscape-design/components/property-filter";
import type { PropertyFilterProps } from "@cloudscape-design/components/property-filter";
import Select from "@cloudscape-design/components/select";
import SpaceBetween from "@cloudscape-design/components/space-between";
import Table from "@cloudscape-design/components/table";
import type { TableProps } from "@cloudscape-design/components/table";
import { useRouter } from "next/navigation";
import { useMemo, useRef, useState } from "react";

import { SearchModeNote } from "@/components/common/search-mode-note";
import { TablePreferencesButton } from "@/components/common/table-preferences";
import { InfoLink } from "@/components/shell/help-context";
import { useFollow } from "@/hooks/use-follow";
import { usePropertyOperatorCompletion } from "@/hooks/use-property-operator-completion";
import { useRecords } from "@/hooks/use-records";
import { useShortcut } from "@/hooks/use-shortcuts";
import { useTablePreferences } from "@/hooks/use-table-preferences";
import type { ColumnChoice } from "@/hooks/use-table-preferences";
import type { HostedZone, RecordSet } from "@/lib/api/types";
import { displayName, formatNumber, orDash, routingPolicyLabel } from "@/lib/format";
import {
  CONTAINS_ONLY,
  EMPTY_QUERY,
  EQUALS_ONLY,
  matchesText,
  NUMBER_OPERATORS,
  toApiFilters,
} from "@/lib/property-filter";
import { differentiator, recordTargets } from "@/lib/record-draft";
import { filterableRecordTypes, routingPolicies } from "@/lib/record-types";
import { routes } from "@/lib/routes";
import styles from "./records-table.module.css";
import { ValueLines } from "./value-lines";

const COLUMNS: ColumnChoice[] = [
  { id: "name", label: "Record name" },
  { id: "type", label: "Type" },
  { id: "routing_policy", label: "Routing policy" },
  { id: "differentiator", label: "Differentiator" },
  { id: "alias", label: "Alias" },
  { id: "value", label: "Value/Route traffic to" },
  { id: "ttl", label: "TTL (seconds)" },
  { id: "health_check_id", label: "Health check ID" },
  { id: "evaluate_target_health", label: "Evaluate target health" },
  { id: "set_identifier", label: "Record ID" },
];

const FILTERING_PROPERTIES: PropertyFilterProps.FilteringProperty[] = [
  {
    key: "name",
    propertyLabel: "Record name",
    groupValuesLabel: "Record name values",
    operators: CONTAINS_ONLY,
    defaultOperator: ":",
  },
  {
    key: "type",
    propertyLabel: "Type",
    groupValuesLabel: "Type values",
    operators: EQUALS_ONLY,
    defaultOperator: "=",
  },
  {
    key: "routing_policy",
    propertyLabel: "Routing policy",
    groupValuesLabel: "Routing policy values",
    operators: EQUALS_ONLY,
    defaultOperator: "=",
  },
  {
    key: "differentiator",
    propertyLabel: "Differentiator",
    groupValuesLabel: "Differentiator values",
    operators: CONTAINS_ONLY,
    defaultOperator: ":",
  },
  {
    key: "alias",
    propertyLabel: "Alias",
    groupValuesLabel: "Alias values",
    operators: EQUALS_ONLY,
    defaultOperator: "=",
  },
  {
    key: "value",
    propertyLabel: "Value/Route traffic to",
    groupValuesLabel: "Values",
    operators: CONTAINS_ONLY,
    defaultOperator: ":",
  },
  {
    key: "ttl",
    propertyLabel: "TTL (seconds)",
    groupValuesLabel: "TTL values",
    operators: NUMBER_OPERATORS,
    defaultOperator: "=",
  },
  {
    key: "health_check_id",
    propertyLabel: "Health check ID",
    groupValuesLabel: "Health check ID values",
    operators: CONTAINS_ONLY,
    defaultOperator: ":",
  },
  {
    key: "evaluate_target_health",
    propertyLabel: "Evaluate target health",
    groupValuesLabel: "Evaluate target health values",
    operators: EQUALS_ONLY,
    defaultOperator: "=",
  },
  {
    key: "set_identifier",
    propertyLabel: "Record ID",
    groupValuesLabel: "Record ID values",
    operators: CONTAINS_ONLY,
    defaultOperator: ":",
  },
];

const TYPE_OPTIONS = filterableRecordTypes.map((type) => ({ value: type, label: type }));
const POLICY_OPTIONS = routingPolicies.map((policy) => ({
  value: policy.shortLabel,
  label: policy.shortLabel,
}));
const ALIAS_OPTIONS = [
  { value: "Alias", label: "Alias" },
  { value: "Non-alias", label: "Non-alias" },
];

const FILTERING_OPTIONS: PropertyFilterProps.FilteringOption[] = [
  ...TYPE_OPTIONS.map((option) => ({ propertyKey: "type", value: option.value })),
  ...POLICY_OPTIONS.map((option) => ({ propertyKey: "routing_policy", value: option.value })),
  ...ALIAS_OPTIONS.map((option) => ({ propertyKey: "alias", value: option.value })),
  ...["Yes", "No"].map((value) => ({ propertyKey: "evaluate_target_health", value })),
];

/** Convert a displayed filter value into the one the API stores. */
function toApiValue(field: string, value: string): string {
  if (field === "routing_policy") {
    return (
      routingPolicies.find((policy) => policy.shortLabel.toLowerCase() === value.toLowerCase())
        ?.value ?? value
    );
  }
  if (field === "alias")
    return value.toLowerCase() === "alias" || value.toLowerCase() === "yes" ? "yes" : "no";
  if (field === "evaluate_target_health") return value.toLowerCase() === "yes" ? "yes" : "no";
  return value;
}

type Sorting = { field: string; descending: boolean } | null;

interface RecordsTableProps {
  zone: HostedZone;
  selected: RecordSet[];
  onSelectionChange: (records: RecordSet[]) => void;
  onDelete: () => void;
}

/** The value of the quick-filter select for a property: its `=` token, if there is one. */
function quickFilterValue(query: PropertyFilterProps.Query, property: string): string | null {
  const token = query.tokens.find(
    (candidate) => candidate.propertyKey === property && candidate.operator === "=",
  );
  return token ? String(token.value) : null;
}

export function RecordsTable({ zone, selected, onSelectionChange, onDelete }: RecordsTableProps) {
  const router = useRouter();
  const follow = useFollow();
  const filterRef = useRef<PropertyFilterProps.Ref>(null);
  const preferencesRef = useRef<HTMLDivElement>(null);
  const filterContainer = usePropertyOperatorCompletion(FILTERING_PROPERTIES);

  const [preferences, setPreferences] = useTablePreferences("records", COLUMNS);
  const [query, setQuery] = useState(EMPTY_QUERY);
  const [sorting, setSorting] = useState<Sorting>(null);
  const [page, setPage] = useState(1);

  const pageSize = preferences.pageSize ?? 100;
  const { filters, filterMode } = useMemo(() => toApiFilters(query, toApiValue), [query]);
  const records = useRecords(zone.id, {
    filters,
    filterMode,
    sort: sorting?.field,
    order: sorting?.descending ? "desc" : "asc",
    page,
    pageSize,
  });

  const items = records.data?.items ?? [];
  const total = records.data?.total ?? 0;
  const filtering = query.tokens.length > 0;
  // Keep showing the selection even after a refetch replaced the row objects.
  const selectedIds = new Set(selected.map((record) => record.id));
  const selectedItems = items.filter((record) => selectedIds.has(record.id));

  useShortcut("/", "Focus the filter", () => filterRef.current?.focus());
  useShortcut("c", "Create a record", () => router.push(routes.createRecord(zone.id)));
  useShortcut("i", "Import a zone file", () => router.push(routes.importZoneFile(zone.id)));
  useShortcut("r", "Refresh the records", () => void records.refetch());
  useShortcut("Delete", "Delete the selected records", onDelete, selected.length > 0);

  const changeQuery = (next: PropertyFilterProps.Query) => {
    setQuery(next);
    setPage(1);
    onSelectionChange([]);
  };

  /** The Type / Routing policy / Alias selects add, replace or remove one `=` token. */
  const setQuickFilter = (property: string, value: string | null) => {
    const others = query.tokens.filter(
      (token) => !(token.propertyKey === property && token.operator === "="),
    );
    changeQuery({
      ...query,
      tokens:
        value === null ? others : [...others, { propertyKey: property, operator: "=", value }],
    });
  };

  const quickFilter = (
    property: string,
    placeholder: string,
    options: { value: string; label: string }[],
  ) => {
    const value = quickFilterValue(query, property);
    return (
      <div className={styles[property]}>
        <Select
          placeholder={placeholder}
          ariaLabel={`Filter by ${placeholder.toLowerCase()}`}
          selectedOption={options.find((option) => option.value === value) ?? null}
          options={options}
          filteringType="auto"
          filteringAriaLabel={`Find ${placeholder.toLowerCase()}`}
          onChange={({ detail }) => setQuickFilter(property, detail.selectedOption.value ?? null)}
          expandToViewport
        />
      </div>
    );
  };

  const columnDefinitions: TableProps.ColumnDefinition<RecordSet>[] = [
    {
      id: "name",
      header: "Record name",
      sortingField: "name",
      isRowHeader: true,
      minWidth: 220,
      width: 380,
      cell: (record) => displayName(record.name),
    },
    { id: "type", header: "Type", sortingField: "type", width: 90, cell: (record) => record.type },
    {
      id: "routing_policy",
      header: "Routing policy",
      sortingField: "routing_policy",
      width: 120,
      cell: (record) => routingPolicyLabel[record.routing_policy],
    },
    {
      id: "differentiator",
      header: "Differentiator",
      sortingField: "differentiator",
      width: 110,
      cell: (record) => orDash(differentiator(record)),
    },
    {
      id: "alias",
      header: "Alias",
      sortingField: "alias",
      width: 110,
      cell: (record) => (record.alias ? "Yes" : "No"),
    },
    {
      id: "value",
      header: "Value/Route traffic to",
      sortingField: "value",
      width: 240,
      cell: (record) => <ValueLines values={recordTargets(record)} />,
    },
    {
      id: "ttl",
      header: "TTL (seconds)",
      sortingField: "ttl",
      width: 110,
      cell: (record) => (record.ttl === null ? "-" : formatNumber(record.ttl)),
    },
    {
      id: "health_check_id",
      header: "Health check ID",
      sortingField: "health_check_id",
      width: 120,
      cell: (record) => orDash(record.health_check_id),
    },
    {
      id: "evaluate_target_health",
      header: "Evaluate target health",
      sortingField: "evaluate_target_health",
      width: 120,
      cell: (record) =>
        record.alias_target ? (record.alias_target.evaluate_target_health ? "Yes" : "No") : "-",
    },
    {
      id: "set_identifier",
      header: "Record ID",
      sortingField: "set_identifier",
      minWidth: 120,
      cell: (record) => orDash(record.set_identifier),
    },
  ];

  const empty = filtering ? (
    <Box textAlign="center" color="inherit" padding={{ vertical: "l" }}>
      <SpaceBetween size="xs">
        <div>
          <b>No matches</b>
          <Box variant="p" color="inherit">
            No results match your query.
          </Box>
        </div>
        <Button onClick={() => changeQuery(EMPTY_QUERY)}>Clear filters</Button>
      </SpaceBetween>
    </Box>
  ) : (
    <Box textAlign="center" color="inherit" padding={{ vertical: "l" }}>
      <b>No records</b>
    </Box>
  );

  return (
    <Table
      variant="container"
      stickyHeader
      resizableColumns
      enableKeyboardNavigation
      trackBy="id"
      items={items}
      columnDefinitions={columnDefinitions}
      visibleColumns={preferences.visibleContent}
      wrapLines={preferences.wrapLines}
      loading={records.isPending}
      loadingText="Loading records"
      skeleton={{ totalRows: 6 }}
      empty={empty}
      selectionType="multi"
      selectedItems={selectedItems}
      onSelectionChange={({ detail }) => onSelectionChange(detail.selectedItems)}
      ariaLabels={{
        selectionGroupLabel: "Records selection",
        allItemsSelectionLabel: () => `${selected.length} Records selected`,
        itemSelectionLabel: (_data, record) =>
          `${displayName(record.name)} is ${selectedIds.has(record.id) ? "" : "not "}selected`,
        tableLabel: "Records",
      }}
      sortingColumn={sorting ? { sortingField: sorting.field } : undefined}
      sortingDescending={sorting?.descending}
      onSortingChange={({ detail }) => {
        setSorting({
          field: detail.sortingColumn.sortingField ?? "name",
          descending: detail.isDescending ?? false,
        });
        setPage(1);
      }}
      header={
        <Header
          variant="h2"
          info={<InfoLink topic="records" />}
          // The counter is the size of the zone; "n matches" reports what the filter found.
          counter={
            selected.length > 0
              ? `(${selected.length}/${formatNumber(zone.record_count)})`
              : `(${formatNumber(zone.record_count)})`
          }
          description={
            <SearchModeNote
              onOpenSettings={() => preferencesRef.current?.querySelector("button")?.click()}
            />
          }
          actions={
            <SpaceBetween direction="horizontal" size="xs">
              <Button
                iconName="refresh"
                ariaLabel="Refresh records"
                loading={records.isFetching && !records.isPending}
                onClick={() => void records.refetch()}
              />
              <Button disabled={selected.length === 0} onClick={onDelete}>
                {selected.length > 1 ? "Delete records" : "Delete record"}
              </Button>
              <Button href={routes.importZoneFile(zone.id)} onFollow={follow}>
                Import zone file
              </Button>
              <Button variant="primary" href={routes.createRecord(zone.id)} onFollow={follow}>
                Create record
              </Button>
            </SpaceBetween>
          }
        >
          Records
        </Header>
      }
      filter={
        <div className={styles.filterRow}>
          <div className={styles.filters}>
            <div className={styles.propertyFilter} ref={filterContainer}>
              <PropertyFilter
                ref={filterRef}
                query={query}
                onChange={({ detail }) => changeQuery(detail)}
                filteringProperties={FILTERING_PROPERTIES}
                filteringOptions={FILTERING_OPTIONS}
                filteringPlaceholder="Filter records by property or value"
                filteringAriaLabel="Filter records by property or value"
                countText={filtering && records.data ? matchesText(total) : undefined}
                expandToViewport
              />
            </div>
            {quickFilter("type", "Type", TYPE_OPTIONS)}
            {quickFilter("routing_policy", "Routing policy", POLICY_OPTIONS)}
            {quickFilter("alias", "Alias", ALIAS_OPTIONS)}
            {/* The console repeats the match count after the selects. */}
            {filtering && records.data && (
              <span className={styles.count} aria-hidden="true">
                {matchesText(total)}
              </span>
            )}
          </div>
        </div>
      }
      pagination={
        <Pagination
          currentPageIndex={page}
          pagesCount={records.data?.pages ?? 1}
          onChange={({ detail }) => setPage(detail.currentPageIndex)}
        />
      }
      preferences={
        <div ref={preferencesRef}>
          <TablePreferencesButton
            columns={COLUMNS}
            preferences={preferences}
            onConfirm={(next) => {
              setPreferences(next);
              setPage(1);
            }}
          />
        </div>
      }
    />
  );
}
