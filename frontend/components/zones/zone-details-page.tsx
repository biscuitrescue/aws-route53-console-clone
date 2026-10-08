"use client";

import Badge from "@cloudscape-design/components/badge";
import Box from "@cloudscape-design/components/box";
import Button from "@cloudscape-design/components/button";
import ButtonDropdown from "@cloudscape-design/components/button-dropdown";
import ColumnLayout from "@cloudscape-design/components/column-layout";
import Container from "@cloudscape-design/components/container";
import ContentLayout from "@cloudscape-design/components/content-layout";
import ExpandableSection from "@cloudscape-design/components/expandable-section";
import Header from "@cloudscape-design/components/header";
import SpaceBetween from "@cloudscape-design/components/space-between";
import SplitPanel from "@cloudscape-design/components/split-panel";
import StatusIndicator from "@cloudscape-design/components/status-indicator";
import Table from "@cloudscape-design/components/table";
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
import { zoneDetailItems } from "./zone-details-list";

function TagsTab({ zone }: { zone: HostedZone }) {
  const follow = useFollow();
  return (
    <Table
      variant="container"
      items={zone.tags}
      trackBy="key"
      header={
        <Header
          variant="h2"
          actions={
            <Button href={routes.editHostedZone(zone.id)} onFollow={follow}>
              Manage tags
            </Button>
          }
        >
          Tags
        </Header>
      }
      columnDefinitions={[
        { id: "key", header: "Key", cell: (tag) => tag.key, isRowHeader: true },
        { id: "value", header: "Value", cell: (tag) => tag.value || "-" },
      ]}
      empty={
        <Box textAlign="center" color="inherit" padding={{ vertical: "l" }}>
          <b>No tags</b>
          <Box variant="p" color="inherit">
            No tags associated with the resource.
          </Box>
        </Box>
      }
    />
  );
}

function DnssecTab() {
  return (
    <Container
      header={
        <Header variant="h2" actions={<Button disabled>Enable DNSSEC signing</Button>}>
          DNSSEC signing
        </Header>
      }
    >
      <SpaceBetween size="m">
        <div>
          <Box variant="awsui-key-label">DNSSEC signing status</Box>
          <StatusIndicator type="stopped">Not signing</StatusIndicator>
        </div>
        <Box>
          <b>You have not enabled DNSSEC signing for this hosted zone</b>
        </Box>
        <Box color="text-body-secondary">DNSSEC signing is coming soon in this clone.</Box>
      </SpaceBetween>
    </Container>
  );
}

function AcceleratedRecoveryTab() {
  return (
    <Container
      header={
        <Header
          variant="h2"
          actions={<Button disabled>Enable</Button>}
          description="Enable the accelerated recovery option to ensure that you can continue to make changes to your public DNS records after an impairment to US East (N. Virginia)."
        >
          Accelerated recovery
        </Header>
      }
    >
      <SpaceBetween size="m">
        <div>
          <Box variant="awsui-key-label">Status</Box>
          <StatusIndicator type="stopped">Disabled</StatusIndicator>
        </div>
        <Box color="text-body-secondary">Accelerated recovery is coming soon in this clone.</Box>
      </SpaceBetween>
    </Container>
  );
}

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
            <BulkTtlForm zoneId={zone.id} records={selected} onSaved={() => changeSelection([])} />
          )}
        </SplitPanel>
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
            <ColumnLayout columns={3} variant="text-grid">
              {zoneDetailItems(zone).map((item) => (
                <div key={item.label}>
                  <Box variant="awsui-key-label">{item.label}</Box>
                  <div>{item.value}</div>
                </div>
              ))}
            </ColumnLayout>
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
