"use client";

import Box from "@cloudscape-design/components/box";
import Button from "@cloudscape-design/components/button";
import Header from "@cloudscape-design/components/header";
import Link from "@cloudscape-design/components/link";
import Pagination from "@cloudscape-design/components/pagination";
import PropertyFilter from "@cloudscape-design/components/property-filter";
import type { PropertyFilterProps } from "@cloudscape-design/components/property-filter";
import SpaceBetween from "@cloudscape-design/components/space-between";
import SplitPanel from "@cloudscape-design/components/split-panel";
import Table from "@cloudscape-design/components/table";
import type { TableProps } from "@cloudscape-design/components/table";
import { useRouter, useSearchParams } from "next/navigation";
import { useEffect, useMemo, useRef, useState } from "react";

import { SearchModeNote } from "@/components/common/search-mode-note";
import { TablePreferencesButton } from "@/components/common/table-preferences";
import { ConsolePage } from "@/components/shell/console-page";
import { useFollow } from "@/hooks/use-follow";
import { useHostedZone, useHostedZones } from "@/hooks/use-hosted-zones";
import { usePropertyOperatorCompletion } from "@/hooks/use-property-operator-completion";
import { useShortcut } from "@/hooks/use-shortcuts";
import { useTablePreferences } from "@/hooks/use-table-preferences";
import type { ColumnChoice } from "@/hooks/use-table-preferences";
import type { HostedZoneSummary } from "@/lib/api/types";
import { displayName, formatNumber, orDash, zoneTypeLabel } from "@/lib/format";
import {
  CONTAINS_ONLY,
  EMPTY_QUERY,
  EQUALS_ONLY,
  matchesText,
  NUMBER_OPERATORS,
  toApiFilters,
} from "@/lib/property-filter";
import { pathForConsoleHash, routes } from "@/lib/routes";

import { DeleteZoneModal } from "./delete-zone-modal";
import { ZoneDetailsList } from "./zone-details-list";

const COLUMNS: ColumnChoice[] = [
  { id: "name", label: "Hosted zone name" },
  { id: "type", label: "Type" },
  { id: "accelerated_recovery", label: "Accelerated recovery", hiddenByDefault: true },
  { id: "created_by", label: "Created by" },
  { id: "record_count", label: "Record count" },
  { id: "description", label: "Description" },
  { id: "id", label: "Hosted zone ID" },
];

const FILTERING_PROPERTIES: PropertyFilterProps.FilteringProperty[] = [
  {
    key: "name",
    propertyLabel: "Hosted zone name",
    groupValuesLabel: "Hosted zone name values",
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
    key: "accelerated_recovery",
    propertyLabel: "Accelerated recovery",
    groupValuesLabel: "Accelerated recovery values",
    operators: CONTAINS_ONLY,
    defaultOperator: ":",
  },
  {
    key: "created_by",
    propertyLabel: "Created by",
    groupValuesLabel: "Created by values",
    operators: CONTAINS_ONLY,
    defaultOperator: ":",
  },
  {
    key: "record_count",
    propertyLabel: "Record count",
    groupValuesLabel: "Record count values",
    operators: NUMBER_OPERATORS,
    defaultOperator: "=",
  },
  {
    key: "description",
    propertyLabel: "Description",
    groupValuesLabel: "Description values",
    operators: CONTAINS_ONLY,
    defaultOperator: ":",
  },
  {
    key: "id",
    propertyLabel: "Hosted zone ID",
    groupValuesLabel: "Hosted zone ID values",
    operators: CONTAINS_ONLY,
    defaultOperator: ":",
  },
];

/** Accelerated recovery is outside the clone's scope, so every zone has it off. */
const ACCELERATED_RECOVERY = "Disabled";

const TYPE_OPTIONS: PropertyFilterProps.FilteringOption[] = [
  { propertyKey: "type", value: "Public" },
  { propertyKey: "type", value: "Private" },
];

/** `null` until the user sorts: the API's default order is Route 53's own. */
type Sorting = { field: string; descending: boolean } | null;

function initialQuery(search: string | null): PropertyFilterProps.Query {
  return search ? { operation: "and", tokens: [{ operator: ":", value: search }] } : EMPTY_QUERY;
}

export function HostedZonesPage() {
  const router = useRouter();
  const follow = useFollow();
  const searchParams = useSearchParams();
  const filterRef = useRef<PropertyFilterProps.Ref>(null);
  const preferencesRef = useRef<HTMLDivElement>(null);
  const filterContainer = usePropertyOperatorCompletion(FILTERING_PROPERTIES);

  const [preferences, setPreferences] = useTablePreferences("hostedZones", COLUMNS);
  const [query, setQuery] = useState(() => initialQuery(searchParams.get("search")));
  const [sorting, setSorting] = useState<Sorting>(null);
  const [page, setPage] = useState(1);
  const [selectedId, setSelectedId] = useState<string | null>(null);
  const [panelOpen, setPanelOpen] = useState(false);
  const [deleting, setDeleting] = useState<HostedZoneSummary | null>(null);

  // Links copied from the real console use hash routes; send them to the matching page.
  useEffect(() => {
    const path = pathForConsoleHash(window.location.hash);
    if (path) router.replace(path);
  }, [router]);

  const pageSize = preferences.pageSize ?? 100;
  const { filters, filterMode } = useMemo(() => toApiFilters(query), [query]);
  const zones = useHostedZones({
    filters,
    filterMode,
    sort: sorting?.field,
    order: sorting?.descending ? "desc" : "asc",
    page,
    pageSize,
  });

  const items = zones.data?.items ?? [];
  const matches = zones.data?.total ?? 0;
  const selected = items.find((zone) => zone.id === selectedId) ?? null;
  const filtering = query.tokens.length > 0;
  // The header counts every zone; "n matches" reports what the filter found.
  const everyZone = useHostedZones({ page: 1, pageSize: 1 }, { enabled: filtering });
  const total = filtering ? (everyZone.data?.total ?? matches) : matches;
  const details = useHostedZone(selected?.id ?? "", { enabled: selected !== null });

  useShortcut("/", "Focus the filter", () => filterRef.current?.focus());
  useShortcut("c", "Create a hosted zone", () => router.push(routes.createHostedZone));
  useShortcut("r", "Refresh the list", () => void zones.refetch());

  const columnDefinitions: TableProps.ColumnDefinition<HostedZoneSummary>[] = [
    {
      id: "name",
      header: "Hosted zone name",
      sortingField: "name",
      isRowHeader: true,
      width: 250,
      cell: (zone) => (
        <Link href={routes.hostedZone(zone.id)} onFollow={follow}>
          {displayName(zone.name)}
        </Link>
      ),
    },
    {
      id: "type",
      width: 260,
      header: "Type",
      sortingField: "type",
      cell: (zone) => zoneTypeLabel[zone.type],
    },
    {
      id: "accelerated_recovery",
      header: "Accelerated recovery",
      width: 200,
      cell: () => ACCELERATED_RECOVERY,
    },
    {
      id: "created_by",
      header: "Created by",
      width: 260,
      sortingField: "created_by",
      cell: (zone) => zone.created_by,
    },
    {
      id: "record_count",
      header: "Record count",
      width: 260,
      sortingField: "record_count",
      cell: (zone) => formatNumber(zone.record_count),
    },
    {
      id: "description",
      header: "Description",
      width: 260,
      sortingField: "description",
      cell: (zone) => orDash(zone.description),
    },
    {
      id: "id",
      header: "Hosted zone ID",
      sortingField: "id",
      minWidth: 240,
      cell: (zone) => zone.id,
    },
  ];

  /** Selecting a zone opens its details panel, as in the console. */
  const select = (zoneId: string | null) => {
    setSelectedId(zoneId);
    if (zoneId) setPanelOpen(true);
  };

  const clearFilters = () => {
    setQuery(EMPTY_QUERY);
    setPage(1);
  };

  const empty = filtering ? (
    <Box textAlign="center" color="inherit" padding={{ vertical: "l" }}>
      <SpaceBetween size="xs">
        <div>
          <b>No matches</b>
          <Box variant="p" color="inherit">
            No results match your query.
          </Box>
        </div>
        <Button onClick={clearFilters}>Clear filters</Button>
      </SpaceBetween>
    </Box>
  ) : (
    <Box textAlign="center" color="inherit" padding={{ vertical: "l" }}>
      <SpaceBetween size="xs">
        <div>
          <b>No hosted zones</b>
          <Box variant="p" color="inherit">
            There are no hosted zones created for this account.
          </Box>
        </div>
        <Button variant="primary" href={routes.createHostedZone} onFollow={follow}>
          Create hosted zone
        </Button>
      </SpaceBetween>
    </Box>
  );

  return (
    <ConsolePage
      title="Hosted zones | Route 53"
      helpTopic="hosted-zones"
      contentType="table"
      breadcrumbs={[{ text: "Hosted zones", href: routes.hostedZones }]}
      splitPanelOpen={panelOpen}
      onSplitPanelToggle={setPanelOpen}
      splitPanel={
        <SplitPanel
          header={selected ? "Hosted zone details" : "0 hosted zone selected"}
          closeBehavior="collapse"
        >
          {!selected && <Box>Select a hosted zone to see its details</Box>}
          {selected && details.data && <ZoneDetailsList zone={details.data} stacked />}
        </SplitPanel>
      }
    >
      <Table
        variant="full-page"
        stickyHeader
        resizableColumns
        enableKeyboardNavigation
        trackBy="id"
        items={items}
        columnDefinitions={columnDefinitions}
        visibleColumns={preferences.visibleContent}
        wrapLines={preferences.wrapLines}
        loading={zones.isPending}
        loadingText="Loading hosted zones"
        skeleton={{ totalRows: 6 }}
        empty={empty}
        selectionType="single"
        selectedItems={selected ? [selected] : []}
        onSelectionChange={({ detail }) => select(detail.selectedItems[0]?.id ?? null)}
        onRowClick={({ detail }) => select(detail.item.id)}
        ariaLabels={{
          selectionGroupLabel: "Hosted zones selection",
          itemSelectionLabel: (_data, zone) =>
            `${displayName(zone.name)} is ${zone.id === selectedId ? "" : "not "}selected`,
          tableLabel: "Hosted zones",
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
            variant="awsui-h1-sticky"
            counter={selected ? `(1/${formatNumber(total)})` : `(${formatNumber(total)})`}
            description={
              <SearchModeNote
                onOpenSettings={() => preferencesRef.current?.querySelector("button")?.click()}
              />
            }
            actions={
              <SpaceBetween direction="horizontal" size="xs">
                <Button
                  iconName="refresh"
                  ariaLabel="Refresh hosted zones"
                  loading={zones.isFetching && !zones.isPending}
                  onClick={() => void zones.refetch()}
                />
                <Button
                  disabled={!selected}
                  href={selected ? routes.hostedZone(selected.id) : undefined}
                  onFollow={follow}
                >
                  View details
                </Button>
                <Button
                  disabled={!selected}
                  href={selected ? routes.editHostedZone(selected.id) : undefined}
                  onFollow={follow}
                >
                  Edit
                </Button>
                <Button disabled={!selected} onClick={() => setDeleting(selected)}>
                  Delete
                </Button>
                <Button variant="primary" href={routes.createHostedZone} onFollow={follow}>
                  Create hosted zone
                </Button>
              </SpaceBetween>
            }
          >
            Hosted zones
          </Header>
        }
        filter={
          <div ref={filterContainer}>
            <PropertyFilter
              ref={filterRef}
              query={query}
              onChange={({ detail }) => {
                setQuery(detail);
                setPage(1);
              }}
              filteringProperties={FILTERING_PROPERTIES}
              filteringOptions={[
                ...TYPE_OPTIONS,
                { propertyKey: "accelerated_recovery", value: ACCELERATED_RECOVERY },
                ...items.map((zone) => ({ propertyKey: "name", value: displayName(zone.name) })),
              ]}
              filteringPlaceholder="Filter records by property or value"
              filteringAriaLabel="Filter records by property or value"
              countText={filtering && zones.data ? matchesText(matches) : undefined}
              expandToViewport
            />
          </div>
        }
        pagination={
          <Pagination
            currentPageIndex={page}
            pagesCount={zones.data?.pages ?? 1}
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
      {deleting && (
        <DeleteZoneModal
          zone={deleting}
          onDismiss={() => setDeleting(null)}
          onDeleted={() => {
            setDeleting(null);
            setSelectedId(null);
          }}
        />
      )}
    </ConsolePage>
  );
}
