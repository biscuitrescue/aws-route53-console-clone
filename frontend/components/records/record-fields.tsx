"use client";

import Box from "@cloudscape-design/components/box";
import Button from "@cloudscape-design/components/button";
import ColumnLayout from "@cloudscape-design/components/column-layout";
import FormField from "@cloudscape-design/components/form-field";
import Grid from "@cloudscape-design/components/grid";
import Input from "@cloudscape-design/components/input";
import Select from "@cloudscape-design/components/select";
import SpaceBetween from "@cloudscape-design/components/space-between";
import Textarea from "@cloudscape-design/components/textarea";
import Toggle from "@cloudscape-design/components/toggle";

import { InfoLink } from "@/components/shell/help-context";
import { useRecords } from "@/hooks/use-records";
import { aliasEndpoint, aliasEndpoints, ZONE_RECORD_ENDPOINT } from "@/lib/alias-endpoints";
import type { HostedZone, RecordType, RoutingPolicy } from "@/lib/api/types";
import { awsRegions } from "@/lib/aws-regions";
import { displayName } from "@/lib/format";
import type { RecordDraft, RecordErrors } from "@/lib/record-draft";
import {
  recordTypeInfo,
  recordTypeOptions,
  routingPolicyOptions,
  soaType,
  TTL_PRESETS,
} from "@/lib/record-types";

const CONTINENTS = [
  { value: "AF", label: "Africa" },
  { value: "AN", label: "Antarctica" },
  { value: "AS", label: "Asia" },
  { value: "EU", label: "Europe" },
  { value: "NA", label: "North America" },
  { value: "OC", label: "Oceania" },
  { value: "SA", label: "South America" },
];

const FAILOVER_ROLES = [
  { value: "PRIMARY", label: "Primary" },
  { value: "SECONDARY", label: "Secondary" },
];

const ENDPOINT_OPTIONS = aliasEndpoints.map(({ value, label }) => ({ value, label }));
const ZONE_RECORDS = { page: 1, pageSize: 500 };

interface RecordFieldsProps {
  zone: Pick<HostedZone, "id" | "name">;
  draft: RecordDraft;
  errors: RecordErrors;
  onChange: (change: Partial<RecordDraft>) => void;
  /** Two columns on the create page, one in the narrow side panel. */
  columns: 1 | 2;
  /** The zone's own NS and SOA keep their name, type and routing policy. */
  identityLocked?: boolean;
  /** Put the cursor in the record name when the fields appear. */
  autoFocus?: boolean;
  /** The wizard chooses the routing policy in its first step, so the select is left out. */
  policyFixed?: boolean;
}

/** The fields of one record, shared by quick create and the edit panel. */
export function RecordFields({
  zone,
  draft,
  errors,
  onChange,
  columns,
  identityLocked = false,
  autoFocus = false,
  policyFixed = false,
}: RecordFieldsProps) {
  const typeInfo = recordTypeInfo(draft.type);
  const zoneName = zone.name;
  const typeOptions =
    draft.type === "SOA" ? [{ value: soaType.value, label: soaType.label }] : recordTypeOptions;

  // An alias can point at another record of the same type in this zone.
  const aliasesZoneRecord = draft.alias && draft.aliasEndpoint === ZONE_RECORD_ENDPOINT;
  const siblings = useRecords(
    zone.id,
    { ...ZONE_RECORDS, types: [draft.type] },
    { enabled: aliasesZoneRecord },
  );
  const ownName = `${draft.name.trim() ? `${draft.name.trim().toLowerCase()}.` : ""}${zoneName}`;
  const siblingOptions = (siblings.data?.items ?? [])
    .filter((record) => record.name !== ownName)
    .map((record) => ({ value: displayName(record.name), label: displayName(record.name) }));
  const endpoint = aliasEndpoint(draft.aliasEndpoint);
  // An alias saved before, whose kind of endpoint cannot be told from its target.
  const hasTarget = endpoint !== undefined || draft.aliasDnsName !== "";
  const aliasAllowed = draft.type !== "NS" && draft.type !== "SOA";
  const simpleOnly = draft.type === "NS" || draft.type === "SOA";

  const nameField = (
    <FormField
      label="Record name"
      info={<InfoLink topic="record-name" />}
      constraintText="Keep blank to create a record for the root domain."
      errorText={errors.name}
      stretch
    >
      <Grid gridDefinition={[{ colspan: 6 }, { colspan: 6 }]} disableGutters>
        <Input
          value={draft.name}
          placeholder="subdomain"
          disabled={identityLocked}
          autoFocus={autoFocus}
          spellcheck={false}
          onChange={({ detail }) => onChange({ name: detail.value })}
        />
        <Box padding={{ left: "s", top: "xxs" }}>
          {draft.name.trim() ? "." : ""}
          {displayName(zoneName)}
        </Box>
      </Grid>
    </FormField>
  );

  const typeField = (
    <FormField label="Record type" info={<InfoLink topic="record-type" />} stretch>
      <Select
        selectedOption={typeOptions.find((option) => option.value === draft.type) ?? null}
        options={typeOptions}
        disabled={identityLocked}
        onChange={({ detail }) => {
          const type = detail.selectedOption.value as RecordType;
          const locksPolicy = type === "NS";
          onChange({ type, ...(locksPolicy && { alias: false, routingPolicy: "simple" }) });
        }}
      />
    </FormField>
  );

  const valueField = draft.alias ? (
    <FormField
      label="Route traffic to"
      info={<InfoLink topic="record-value" />}
      errorText={errors.alias}
      stretch
    >
      <SpaceBetween size="xxxs">
        <Select
          placeholder="Choose endpoint"
          ariaLabel="Alias endpoint"
          selectedOption={ENDPOINT_OPTIONS.find((o) => o.value === draft.aliasEndpoint) ?? null}
          options={ENDPOINT_OPTIONS}
          filteringType="auto"
          onChange={({ detail }) => {
            const chosen = aliasEndpoint(detail.selectedOption.value ?? "");
            onChange({
              aliasEndpoint: chosen?.value ?? "",
              aliasDnsName: "",
              aliasHostedZoneId:
                chosen?.value === ZONE_RECORD_ENDPOINT ? zone.id : (chosen?.hostedZoneId ?? ""),
            });
          }}
        />
        {aliasesZoneRecord ? (
          <Select
            placeholder="Choose record"
            ariaLabel="Record to route traffic to"
            selectedOption={siblingOptions.find((o) => o.value === draft.aliasDnsName) ?? null}
            options={siblingOptions}
            filteringType="auto"
            statusType={siblings.isPending ? "loading" : "finished"}
            loadingText="Loading records"
            empty={`No other ${draft.type} records in this hosted zone`}
            onChange={({ detail }) => onChange({ aliasDnsName: detail.selectedOption.value ?? "" })}
          />
        ) : (
          <Select
            placeholder="Choose Region"
            ariaLabel="Region of the endpoint"
            selectedOption={awsRegions.find((r) => r.value === draft.aliasRegion) ?? null}
            options={awsRegions}
            filteringType="auto"
            disabled={endpoint?.hostedZoneId !== undefined}
            onChange={({ detail }) => onChange({ aliasRegion: detail.selectedOption.value ?? "" })}
          />
        )}
        {hasTarget && !aliasesZoneRecord && (
          <>
            <Input
              value={draft.aliasDnsName}
              placeholder="DNS name of the resource, for example d111111abcdef8.cloudfront.net"
              ariaLabel="Alias target DNS name"
              spellcheck={false}
              onChange={({ detail }) => onChange({ aliasDnsName: detail.value })}
            />
            <Input
              value={draft.aliasHostedZoneId}
              placeholder="Hosted zone ID of the resource, for example Z2FDTNDATAQYW2"
              ariaLabel="Alias target hosted zone ID"
              spellcheck={false}
              onChange={({ detail }) => onChange({ aliasHostedZoneId: detail.value })}
            />
          </>
        )}
        {hasTarget && (
          <Box padding={{ top: "xs" }}>
            <Toggle
              checked={draft.evaluateTargetHealth}
              onChange={({ detail }) => onChange({ evaluateTargetHealth: detail.checked })}
            >
              Evaluate target health
            </Toggle>
          </Box>
        )}
      </SpaceBetween>
    </FormField>
  ) : (
    <FormField
      label="Value"
      info={<InfoLink topic="record-value" />}
      constraintText="Enter multiple values on separate lines."
      errorText={errors.values}
      stretch
    >
      <Textarea
        value={draft.values}
        placeholder={typeInfo.placeholder}
        rows={4}
        spellcheck={false}
        onChange={({ detail }) => onChange({ values: detail.value })}
      />
    </FormField>
  );

  const ttlField = !draft.alias && (
    <FormField
      label="TTL (seconds)"
      info={<InfoLink topic="ttl" />}
      constraintText="Recommended values: 60 to 172800 (two days)"
      errorText={errors.ttl}
      stretch
    >
      <div style={{ display: "flex", gap: 8, alignItems: "flex-start" }}>
        <div style={{ flex: 1, minInlineSize: 80 }}>
          <Input
            type="number"
            inputMode="numeric"
            value={draft.ttl}
            ariaLabel="TTL in seconds"
            onChange={({ detail }) => onChange({ ttl: detail.value })}
          />
        </div>
        {TTL_PRESETS.map((preset) => (
          <Button
            key={preset.label}
            formAction="none"
            ariaLabel={`Set TTL to ${preset.seconds} seconds`}
            onClick={() => onChange({ ttl: String(preset.seconds) })}
          >
            {preset.label}
          </Button>
        ))}
      </div>
    </FormField>
  );

  const policyField = !policyFixed && (
    <FormField label="Routing policy" info={<InfoLink topic="routing-policy" />} stretch>
      <Select
        selectedOption={
          routingPolicyOptions.find((option) => option.value === draft.routingPolicy) ?? null
        }
        options={routingPolicyOptions}
        disabled={identityLocked || simpleOnly}
        onChange={({ detail }) =>
          onChange({ routingPolicy: detail.selectedOption.value as RoutingPolicy })
        }
      />
    </FormField>
  );

  const policyDetails = draft.routingPolicy !== "simple" && (
    <ColumnLayout columns={columns}>
      {draft.routingPolicy === "weighted" && (
        <FormField
          label="Weight"
          constraintText="A whole number between 0 and 255."
          errorText={errors.weight}
          stretch
        >
          <Input
            type="number"
            inputMode="numeric"
            value={draft.weight}
            onChange={({ detail }) => onChange({ weight: detail.value })}
          />
        </FormField>
      )}
      {draft.routingPolicy === "latency" && (
        <FormField label="Region" errorText={errors.region} stretch>
          <Select
            placeholder="Choose Region"
            selectedOption={awsRegions.find((region) => region.value === draft.region) ?? null}
            options={awsRegions}
            onChange={({ detail }) => onChange({ region: detail.selectedOption.value ?? "" })}
          />
        </FormField>
      )}
      {draft.routingPolicy === "failover" && (
        <FormField label="Failover record type" errorText={errors.failover} stretch>
          <Select
            placeholder="Choose type"
            selectedOption={FAILOVER_ROLES.find((role) => role.value === draft.failover) ?? null}
            options={FAILOVER_ROLES}
            onChange={({ detail }) =>
              onChange({ failover: detail.selectedOption.value as RecordDraft["failover"] })
            }
          />
        </FormField>
      )}
      {draft.routingPolicy === "geolocation" && (
        <FormField
          label="Location"
          constraintText="Choose a continent, or enter a two-letter country code."
          errorText={errors.location}
          stretch
        >
          <SpaceBetween size="xs">
            <Select
              placeholder="Choose continent"
              selectedOption={
                CONTINENTS.find((continent) => continent.value === draft.continentCode) ?? null
              }
              options={CONTINENTS}
              onChange={({ detail }) =>
                onChange({ continentCode: detail.selectedOption.value ?? "", countryCode: "" })
              }
            />
            <Input
              value={draft.countryCode}
              placeholder="Country code, for example US"
              ariaLabel="Country code"
              onChange={({ detail }) => onChange({ countryCode: detail.value, continentCode: "" })}
            />
          </SpaceBetween>
        </FormField>
      )}
      <FormField
        label="Record ID"
        constraintText="A name that tells this record apart from others with the same name and type."
        errorText={errors.setIdentifier}
        stretch
      >
        <Input
          value={draft.setIdentifier}
          onChange={({ detail }) => onChange({ setIdentifier: detail.value })}
        />
      </FormField>
    </ColumnLayout>
  );

  const aliasToggle = (
    <Toggle
      checked={draft.alias}
      disabled={!aliasAllowed}
      onChange={({ detail }) => onChange({ alias: detail.checked })}
    >
      Alias
    </Toggle>
  );

  if (columns === 1) {
    return (
      <SpaceBetween size="l">
        {nameField}
        {typeField}
        {aliasToggle}
        {valueField}
        {ttlField}
        {policyField}
        {policyDetails}
      </SpaceBetween>
    );
  }
  return (
    <SpaceBetween size="l">
      <ColumnLayout columns={2}>
        {nameField}
        {typeField}
      </ColumnLayout>
      {aliasToggle}
      {valueField}
      {/* Alias records have no TTL, and the routing policy takes its place. */}
      <ColumnLayout columns={2}>
        {ttlField || policyField}
        {ttlField ? policyField : <div />}
      </ColumnLayout>
      {policyDetails}
    </SpaceBetween>
  );
}
