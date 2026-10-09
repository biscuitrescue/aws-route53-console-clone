"use client";

import { useCollection } from "@cloudscape-design/collection-hooks";
import Box from "@cloudscape-design/components/box";
import Button from "@cloudscape-design/components/button";
import ColumnLayout from "@cloudscape-design/components/column-layout";
import Modal from "@cloudscape-design/components/modal";
import Pagination from "@cloudscape-design/components/pagination";
import SpaceBetween from "@cloudscape-design/components/space-between";
import Table from "@cloudscape-design/components/table";
import TextFilter from "@cloudscape-design/components/text-filter";

import { useNotify } from "@/components/shell/notifications";
import { useChangeRecords } from "@/hooks/use-records";
import type { RecordSet } from "@/lib/api/types";
import { displayName } from "@/lib/format";
import { recordIdentity, recordTargets } from "@/lib/record-draft";

import { ValueLines } from "./value-lines";

interface DeleteRecordsModalProps {
  zoneId: string;
  records: RecordSet[];
  onDismiss: () => void;
  onDeleted: () => void;
}

/** Confirmation dialog listing the records about to be deleted in one atomic batch. */
export function DeleteRecordsModal({
  zoneId,
  records,
  onDismiss,
  onDeleted,
}: DeleteRecordsModalProps) {
  const notify = useNotify();
  const changeRecords = useChangeRecords(zoneId);
  const several = records.length > 1;

  const { items, collectionProps, filterProps, paginationProps } = useCollection(records, {
    filtering: {
      filteringFunction: (record, text) =>
        `${record.name} ${record.type} ${recordTargets(record).join(" ")}`
          .toLowerCase()
          .includes(text.toLowerCase()),
    },
    pagination: { pageSize: 5 },
  });

  const submit = () => {
    changeRecords.mutate(
      records.map((record) => ({ action: "DELETE" as const, record_set: recordIdentity(record) })),
      {
        onSuccess: () => {
          notify.success(
            several
              ? "The records were successfully deleted."
              : "The record was successfully deleted.",
          );
          onDeleted();
        },
        onError: (error) => {
          notify.error(error);
          onDismiss();
        },
      },
    );
  };

  return (
    <Modal
      visible
      onDismiss={onDismiss}
      header={several ? `Delete ${records.length} selected records?` : "Delete selected record?"}
      closeAriaLabel="Close modal"
      footer={
        <Box float="right">
          <SpaceBetween direction="horizontal" size="xs">
            <Button variant="link" onClick={onDismiss}>
              Cancel
            </Button>
            <Button variant="primary" loading={changeRecords.isPending} onClick={submit}>
              Delete
            </Button>
          </SpaceBetween>
        </Box>
      }
    >
      <ColumnLayout borders="horizontal">
        <Box>
          Delete the {several ? "records" : "record"} permanently? This action cannot be undone.
          Your domain might become unavailable on the internet.
        </Box>
        <Table
          {...collectionProps}
          variant="container"
          items={items}
          trackBy="id"
          resizableColumns
          ariaLabels={{ tableLabel: "Records to delete" }}
          filter={
            <TextFilter
              {...filterProps}
              filteringPlaceholder="Search"
              filteringAriaLabel="Search records to delete"
            />
          }
          pagination={<Pagination {...paginationProps} />}
          columnDefinitions={[
            {
              id: "name",
              header: "Record name",
              width: 180,
              cell: (record) => displayName(record.name),
              isRowHeader: true,
            },
            { id: "type", header: "Type", width: 160, cell: (record) => record.type },
            {
              id: "value",
              header: "Value/Route traffic to",
              cell: (record) => <ValueLines values={recordTargets(record)} />,
            },
          ]}
        />
      </ColumnLayout>
    </Modal>
  );
}
