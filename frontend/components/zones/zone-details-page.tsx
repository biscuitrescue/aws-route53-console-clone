"use client";

import Badge from "@cloudscape-design/components/badge";
import Box from "@cloudscape-design/components/box";
import Button from "@cloudscape-design/components/button";
import ButtonDropdown from "@cloudscape-design/components/button-dropdown";
import ContentLayout from "@cloudscape-design/components/content-layout";
import ExpandableSection from "@cloudscape-design/components/expandable-section";
import Header from "@cloudscape-design/components/header";
import SpaceBetween from "@cloudscape-design/components/space-between";
import SplitPanel from "@cloudscape-design/components/split-panel";
import Tabs from "@cloudscape-design/components/tabs";
import { useRouter } from "next/navigation";
import { useState } from "react";

import { PageLoading, ZoneLoadError } from "@/components/common/page-state";
import { DeleteRecordsModal } from "@/components/records/delete-records-modal";
import { BulkTtlForm, EditRecordForm, RecordDetails } from "@/components/records/record-panel";
import { RecordsTable } from "@/components/records/records-table";
import { ConsolePage } from "@/components/shell/console-page";
import { InfoLink } from "@/components/shell/help-context";
import { useNotify } from "@/components/shell/notifications";
import { useFollow } from "@/hooks/use-follow";
import { useHostedZone } from "@/hooks/use-hosted-zones";
import type { HostedZone, RecordSet } from "@/lib/api/types";
import { downloadFrom, zoneExportUrl } from "@/lib/download";
import { displayName, formatNumber, zoneTypeLabel } from "@/lib/format";
import { routes } from "@/lib/routes";

import { DeleteZoneModal } from "./delete-zone-modal";
import { ZoneDetailsList } from "./zone-details-list";
import { AcceleratedRecoveryTab, DnssecTab, TagsTab } from "./zone-tabs";

function ZoneDetails({ zone }: { zone: HostedZone }) {
  const router = useRouter();
  const follow = useFollow();
  const notify = useNotify();
  const name = displayName(zone.name);

  const [tab, setTab] = useState("records");
  const [selected, setSelected] = useState<RecordSet[]>([]);
  const [editingId, setEditingId] = useState<string | null>(null);
  const [deletingRecords, setDeletingRecords] = useState(false);
  const [deletingZone, setDeletingZone] = useState(false);

  const single = selected.length === 1 ? selected[0] : null;
  const editing = single !== null && single.id === editingId;

  const changeSelection = (records: RecordSet[]) => {
    setSelected(records);
    setEditingId(null);
  };

  const panelHeader = editing
    ? "Edit record"
    : single
      ? "Record details"
      : `${selected.length} records selected`;

  const notInClone = (feature: string) => () =>
    notify.info(
      `${feature} is coming soon`,
      "This action is not part of the clone. Hosted zones and records are fully functional.",
    );

  return (
    <ConsolePage
      title={`${name} - details`}
      helpTopic="zone-details"
      contentType="table"
      breadcrumbs={[
        { text: "Hosted zones", href: routes.hostedZones },
        { text: name, href: routes.hostedZone(zone.id) },
      ]}
      splitPanel={
        // Record details belong to the Records tab; the other tabs have no split panel.
        tab === "records" && (
          <SplitPanel header={panelHeader} closeBehavior="collapse">
            {selected.length === 0 && <Box>Select a record to see its details</Box>}
            {single && !editing && (
              <RecordDetails record={single} onEdit={() => setEditingId(single.id)} />
            )}
            {single && editing && (
              <EditRecordForm
                key={single.id}
                zone={zone}
                record={single}
                onClose={() => setEditingId(null)}
                onSaved={() => changeSelection([])}
              />
            )}
            {selected.length > 1 && (
              <BulkTtlForm
                zoneId={zone.id}
                records={selected}
                onSaved={() => changeSelection([])}
              />
            )}
          </SplitPanel>
        )
      }
    >
      <ContentLayout
        header={
          <Header
            variant="h1"
            info={<InfoLink topic="zone-details" />}
            actions={
              <SpaceBetween direction="horizontal" size="xs">
                <ButtonDropdown
                  items={[
                    { id: "bind", text: "Zone file (BIND format)", iconName: "download" },
                    { id: "json", text: "JSON", iconName: "download" },
                  ]}
                  onItemClick={({ detail }) =>
                    downloadFrom(zoneExportUrl(zone.id, detail.id as "bind" | "json"))
                  }
                >
                  Export zone
                </ButtonDropdown>
                <Button onClick={() => setDeletingZone(true)}>Delete zone</Button>
                <Button onClick={notInClone("Test record")}>Test record</Button>
                <Button onClick={notInClone("Query logging")}>Configure query logging</Button>
              </SpaceBetween>
            }
          >
            <Badge color="blue">{zoneTypeLabel[zone.type]}</Badge> {name}
          </Header>
        }
      >
        <SpaceBetween size="l">
          <ExpandableSection
            variant="container"
            headerText="Hosted zone details"
            headerActions={
              <Button href={routes.editHostedZone(zone.id)} onFollow={follow}>
                Edit hosted zone
              </Button>
            }
          >
            <ZoneDetailsList zone={zone} />
          </ExpandableSection>

          <Tabs
            activeTabId={tab}
            onChange={({ detail }) => setTab(detail.activeTabId)}
            ariaLabel="Hosted zone sections"
            tabs={[
              {
                id: "records",
                label: `Records (${formatNumber(zone.record_count)})`,
                content: (
                  <RecordsTable
                    zone={zone}
                    selected={selected}
                    onSelectionChange={changeSelection}
                    onDelete={() => setDeletingRecords(true)}
                  />
                ),
              },
              {
                id: "acceleratedRecovery",
                label: "Accelerated recovery",
                content: <AcceleratedRecoveryTab />,
              },
              { id: "dnssec", label: "DNSSEC signing", content: <DnssecTab /> },
              {
                id: "tags",
                label: `Hosted zone tags (${zone.tags.length})`,
                content: <TagsTab zone={zone} />,
              },
            ]}
          />
        </SpaceBetween>
      </ContentLayout>

      {deletingRecords && selected.length > 0 && (
        <DeleteRecordsModal
          zoneId={zone.id}
          records={selected}
          onDismiss={() => setDeletingRecords(false)}
          onDeleted={() => {
            setDeletingRecords(false);
            changeSelection([]);
          }}
        />
      )}
      {deletingZone && (
        <DeleteZoneModal
          zone={zone}
          showDetailsLink={false}
          onDismiss={() => setDeletingZone(false)}
          onDeleted={() => router.push(routes.hostedZones)}
        />
      )}
    </ConsolePage>
  );
}

export function ZoneDetailsPage({ zoneId }: { zoneId: string }) {
  const zone = useHostedZone(zoneId);
  if (zone.data) return <ZoneDetails zone={zone.data} />;
  return (
    <ConsolePage
      title="Hosted zone - details"
      helpTopic="zone-details"
      breadcrumbs={[{ text: "Hosted zones", href: routes.hostedZones }]}
    >
      {zone.isError ? (
        <ZoneLoadError error={zone.error} />
      ) : (
        <PageLoading label="Loading hosted zone" />
      )}
    </ConsolePage>
  );
}
