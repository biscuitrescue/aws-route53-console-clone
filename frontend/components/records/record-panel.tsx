"use client";

import Box from "@cloudscape-design/components/box";
import Button from "@cloudscape-design/components/button";
import CopyToClipboard from "@cloudscape-design/components/copy-to-clipboard";
import FormField from "@cloudscape-design/components/form-field";
import Input from "@cloudscape-design/components/input";
import SpaceBetween from "@cloudscape-design/components/space-between";
import { useState } from "react";
import type { ReactNode } from "react";

import { useNotify } from "@/components/shell/notifications";
import { useChangeRecords, useUpdateRecord } from "@/hooks/use-records";
import type { HostedZone, RecordSet } from "@/lib/api/types";
import { displayName, formatNumber, orDash, routingPolicyLabel } from "@/lib/format";
import {
  differentiator,
  draftFromRecord,
  draftToInput,
  hasErrors,
  validateDraft,
} from "@/lib/record-draft";
import type { RecordDraft, RecordErrors } from "@/lib/record-draft";
import { TTL_PRESETS } from "@/lib/record-types";

import { RecordFields } from "./record-fields";

function Detail({ label, children }: { label: string; children: ReactNode }) {
  return (
    <div>
      <Box margin={{ bottom: "xxs" }}>{label}</Box>
      <div>{children}</div>
    </div>
  );
}

function Copyable({ text }: { text: string }) {
  return (
    <CopyToClipboard
      variant="inline"
      textToCopy={text}
      copyButtonAriaLabel={`Copy ${text} text to clipboard`}
      copySuccessText="Copied"
      copyErrorText="Failed to copy"
    />
  );
}

/** Read-only details of one record. */
export function RecordDetails({ record, onEdit }: { record: RecordSet; onEdit: () => void }) {
  const target = record.alias ? record.alias_target : null;
  // A flat list, so the panel spaces every entry evenly.
  const details: { label: string; value: ReactNode }[] = [
    { label: "Record name", value: <Copyable text={displayName(record.name)} /> },
    { label: "Record type", value: record.type },
    target
      ? { label: "Route traffic to", value: <Copyable text={target.dns_name} /> }
      : {
          label: "Value",
          value: record.values.map((value) => (
            <div key={value}>
              <Copyable text={value} />
            </div>
          )),
        },
    { label: "Alias", value: target ? "Yes" : "No" },
    target
      ? { label: "Evaluate target health", value: target.evaluate_target_health ? "Yes" : "No" }
      : { label: "TTL (seconds)", value: record.ttl === null ? "-" : formatNumber(record.ttl) },
    { label: "Routing policy", value: routingPolicyLabel[record.routing_policy] },
    ...(record.routing_policy === "simple"
      ? []
      : [
          { label: "Differentiator", value: orDash(differentiator(record)) },
          { label: "Record ID", value: orDash(record.set_identifier) },
        ]),
  ];
  return (
    <SpaceBetween size="l">
      <Button onClick={onEdit}>Edit record</Button>
      {details.map((detail) => (
        <Detail key={detail.label} label={detail.label}>
          {detail.value}
        </Detail>
      ))}
    </SpaceBetween>
  );
}

interface EditRecordFormProps {
  zone: HostedZone;
  record: RecordSet;
  onClose: () => void;
  onSaved: () => void;
}

/** The edit form the console shows in the side panel. */
export function EditRecordForm({ zone, record, onClose, onSaved }: EditRecordFormProps) {
  const notify = useNotify();
  const updateRecord = useUpdateRecord(zone.id);
  const [draft, setDraft] = useState<RecordDraft>(() => draftFromRecord(record, zone.name));
  const [errors, setErrors] = useState<RecordErrors>({});

  const isZoneDefault =
    record.name === zone.name && (record.type === "NS" || record.type === "SOA");

  const change = (update: Partial<RecordDraft>) => {
    const next = { ...draft, ...update };
    setDraft(next);
    // After a failed submit, clear each error as soon as its field is fixed.
    if (hasErrors(errors)) setErrors(validateDraft(next));
  };

  const submit = () => {
    const found = validateDraft(draft);
    setErrors(found);
    if (hasErrors(found)) return;
    updateRecord.mutate(
      { recordId: record.id, changes: draftToInput(draft) },
      {
        onSuccess: ({ record: saved, changeId }) => {
          notify.recordsChanged(`${displayName(saved.name)} was successfully updated.`, changeId);
          onSaved();
        },
        onError: notify.error,
      },
    );
  };

  return (
    <form
      onSubmit={(event) => {
        event.preventDefault();
        submit();
      }}
      noValidate
    >
      <SpaceBetween size="l">
        <RecordFields
          zone={zone}
          draft={draft}
          errors={errors}
          onChange={change}
          columns={1}
          identityLocked={isZoneDefault}
          autoFocus
        />
        <Box float="right">
          <SpaceBetween direction="horizontal" size="xs">
            <Button variant="link" formAction="none" onClick={onClose}>
              Cancel
            </Button>
            <Button variant="primary" formAction="submit" loading={updateRecord.isPending}>
              Save
            </Button>
          </SpaceBetween>
        </Box>
      </SpaceBetween>
    </form>
  );
}

interface BulkEditProps {
  zoneId: string;
  records: RecordSet[];
  onSaved: () => void;
}

/** Change the TTL of every selected record in one atomic batch. */
export function BulkTtlForm({ zoneId, records, onSaved }: BulkEditProps) {
  const notify = useNotify();
  const changeRecords = useChangeRecords(zoneId);
  const [ttl, setTtl] = useState("");
  const [error, setError] = useState<string>();

  const editable = records.filter((record) => !record.alias);
  const skipped = records.length - editable.length;

  const submit = () => {
    if (!/^\d+$/.test(ttl.trim())) {
      setError("TTL must be a whole number of seconds.");
      return;
    }
    setError(undefined);
    changeRecords.mutate(
      editable.map((record) => ({
        action: "UPSERT" as const,
        record_set: {
          name: record.name,
          type: record.type,
          values: record.values,
          ttl: Number(ttl),
          routing_policy: record.routing_policy,
          set_identifier: record.set_identifier,
          weight: record.weight,
          region: record.region,
          failover: record.failover,
          geolocation: record.geolocation,
          health_check_id: record.health_check_id,
        },
      })),
      {
        onSuccess: (result) => {
          notify.recordsChanged(
            `${result.updated} ${result.updated === 1 ? "record was" : "records were"} successfully updated.`,
            result.id,
          );
          onSaved();
        },
        onError: notify.error,
      },
    );
  };

  return (
    <form
      onSubmit={(event) => {
        event.preventDefault();
        submit();
      }}
      noValidate
    >
      <SpaceBetween size="m">
        <Box variant="h3">Edit TTL for selected records</Box>
        <FormField
          label="TTL (seconds)"
          constraintText={
            skipped > 0
              ? `Applies to ${editable.length} of ${records.length} selected records; alias records have no TTL.`
              : "All selected records change together, or none does."
          }
          errorText={error}
          stretch
        >
          <SpaceBetween direction="horizontal" size="xs">
            <Input
              type="number"
              inputMode="numeric"
              value={ttl}
              placeholder="300"
              ariaLabel="New TTL in seconds"
              onChange={({ detail }) => setTtl(detail.value)}
            />
            {TTL_PRESETS.map((preset) => (
              <Button
                key={preset.label}
                formAction="none"
                onClick={() => setTtl(String(preset.seconds))}
              >
                {preset.label}
              </Button>
            ))}
          </SpaceBetween>
        </FormField>
        <Button
          formAction="submit"
          loading={changeRecords.isPending}
          disabled={editable.length === 0}
        >
          Apply to {editable.length} {editable.length === 1 ? "record" : "records"}
        </Button>
      </SpaceBetween>
    </form>
  );
}
