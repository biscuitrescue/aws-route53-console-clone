"use client";

import { useCollection } from "@cloudscape-design/collection-hooks";
import Alert from "@cloudscape-design/components/alert";
import Box from "@cloudscape-design/components/box";
import Button from "@cloudscape-design/components/button";
import Container from "@cloudscape-design/components/container";
import Header from "@cloudscape-design/components/header";
import Pagination from "@cloudscape-design/components/pagination";
import SpaceBetween from "@cloudscape-design/components/space-between";
import StatusIndicator from "@cloudscape-design/components/status-indicator";
import Table from "@cloudscape-design/components/table";
import TextFilter from "@cloudscape-design/components/text-filter";
import { useState } from "react";

import { InfoLink } from "@/components/shell/help-context";
import { useNotify } from "@/components/shell/notifications";
import { useFollow } from "@/hooks/use-follow";
import type { HostedZone, Tag } from "@/lib/api/types";
import { routes } from "@/lib/routes";

/** Says plainly that an action of these tabs is outside the clone's scope. */
function useComingSoon() {
  const notify = useNotify();
  return (feature: string) => () =>
    notify.info(
      `${feature} is coming soon`,
      "This action is not part of the clone. Hosted zones and records are fully functional.",
    );
}

const TAGS_PAGE_SIZE = 20;

export function TagsTab({ zone }: { zone: HostedZone }) {
  const follow = useFollow();
  const [search, setSearch] = useState("");

  const term = search.trim().toLowerCase();
  const matching = term
    ? zone.tags.filter((tag) => `${tag.key}\n${tag.value}`.toLowerCase().includes(term))
    : zone.tags;
  const { items, collectionProps, paginationProps } = useCollection<Tag>(matching, {
    pagination: { pageSize: TAGS_PAGE_SIZE },
    sorting: { defaultState: { sortingColumn: { sortingField: "key" } } },
  });

  const empty = term ? (
    <Box textAlign="center" color="inherit" padding={{ vertical: "l" }}>
      <SpaceBetween size="xs">
        <div>
          <b>No matches</b>
          <Box variant="p" color="inherit">
            No results match your query.
          </Box>
        </div>
        <Button onClick={() => setSearch("")}>Clear filters</Button>
      </SpaceBetween>
    </Box>
  ) : (
    <Box textAlign="center" color="inherit" padding={{ vertical: "l" }}>
      <b>No tags</b>
      <Box variant="p" color="inherit">
        No tags associated with the resource.
      </Box>
    </Box>
  );

  return (
    <Table
      {...collectionProps}
      variant="container"
      items={items}
      trackBy="key"
      empty={empty}
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
      filter={
        <TextFilter
          filteringText={search}
          filteringPlaceholder="Search"
          filteringAriaLabel="Search tags"
          onChange={({ detail }) => setSearch(detail.filteringText)}
        />
      }
      pagination={<Pagination {...paginationProps} />}
      columnDefinitions={[
        {
          id: "key",
          header: "Key",
          sortingField: "key",
          isRowHeader: true,
          cell: (tag) => tag.key,
        },
        { id: "value", header: "Value", sortingField: "value", cell: (tag) => tag.value || "-" },
      ]}
    />
  );
}

export function DnssecTab() {
  const comingSoon = useComingSoon();
  const [explained, setExplained] = useState(true);
  return (
    <SpaceBetween size="l">
      <Container
        header={
          <Header
            variant="h2"
            info={<InfoLink topic="dnssec" />}
            actions={<Button onClick={comingSoon("DNSSEC signing")}>Enable DNSSEC signing</Button>}
          >
            DNSSEC signing
          </Header>
        }
      >
        <div>
          <Box variant="awsui-key-label">DNSSEC signing status</Box>
          <StatusIndicator type="stopped">Not signing</StatusIndicator>
        </div>
        {explained && (
          <Alert
            type="info"
            dismissible
            header="You have not enabled DNSSEC signing for this hosted zone"
            onDismiss={() => setExplained(false)}
          >
            To enable DNSSEC signing and have Route 53 create a key-signing key (KSK) for you,
            choose Enable DNSSEC signing. Next, you must establish a DNSSEC chain of trust for your
            hosted zone. You&apos;ll complete this step after you enable DNSSEC signing.
          </Alert>
        )}
      </Container>
      <Table
        variant="container"
        items={[]}
        header={
          <Header
            variant="h2"
            info={<InfoLink topic="dnssec" />}
            actions={
              <SpaceBetween direction="horizontal" size="xs">
                <Button disabled>View details</Button>
                <Button onClick={comingSoon("The advanced view")}>Switch to advanced view</Button>
              </SpaceBetween>
            }
          >
            Key-signing keys (KSKs)
          </Header>
        }
        pagination={<Pagination currentPageIndex={1} pagesCount={1} />}
        columnDefinitions={[
          { id: "name", header: "Name", cell: () => null },
          { id: "status", header: "Status", cell: () => null },
          { id: "created", header: "Creation date", cell: () => null },
        ]}
        empty={
          <Box textAlign="center" color="inherit">
            No key-signing keys created.
          </Box>
        }
      />
    </SpaceBetween>
  );
}

export function AcceleratedRecoveryTab() {
  const comingSoon = useComingSoon();
  return (
    <Container
      header={
        <Header
          variant="h2"
          info={<InfoLink topic="accelerated-recovery" />}
          actions={<Button onClick={comingSoon("Accelerated recovery")}>Enable</Button>}
          description="Enable the accelerated recovery option to ensure that you can continue to make changes to your public DNS records after an impairment to US East (N. Virginia)."
        >
          Accelerated recovery
        </Header>
      }
    >
      <Box variant="awsui-key-label">Status</Box>
      <StatusIndicator type="stopped">Disabled</StatusIndicator>
    </Container>
  );
}
