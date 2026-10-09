"use client";

import Box from "@cloudscape-design/components/box";
import ExpandableSection from "@cloudscape-design/components/expandable-section";
import Table from "@cloudscape-design/components/table";

import { useRecords } from "@/hooks/use-records";
import type { HostedZone } from "@/lib/api/types";
import { displayName, formatNumber } from "@/lib/format";
import { recordTargets } from "@/lib/record-draft";

import { ValueLines } from "./value-lines";

const PARAMS = { page: 1, pageSize: 100 };

/** The collapsed "View existing records" list under the create-record form. */
export function ExistingRecords({ zone, title }: { zone: HostedZone; title?: string }) {
  const records = useRecords(zone.id, PARAMS);
  return (
    <ExpandableSection
      headerText={
        title ?? (
          <Box variant="span" fontSize="heading-l" fontWeight="normal">
            View existing records
          </Box>
        )
      }
      headerDescription={
        title
          ? undefined
          : `The following table lists the existing records in ${displayName(zone.name)}.`
      }
    >
      <Table
        variant="container"
        items={records.data?.items ?? []}
        trackBy="id"
        loading={records.isPending}
        loadingText="Loading records"
        ariaLabels={{ tableLabel: "Existing records" }}
        columnDefinitions={[
          {
            id: "name",
            header: "Record name",
            cell: (record) => displayName(record.name),
            isRowHeader: true,
          },
          { id: "type", header: "Type", cell: (record) => record.type },
          {
            id: "value",
            header: "Value/Route traffic to",
            cell: (record) => <ValueLines values={recordTargets(record)} />,
          },
          {
            id: "ttl",
            header: "TTL (seconds)",
            cell: (record) => (record.ttl === null ? "-" : formatNumber(record.ttl)),
          },
        ]}
        empty={<Box textAlign="center">No records</Box>}
      />
    </ExpandableSection>
  );
}
