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
import type { RecordType, RoutingPolicy } from "@/lib/api/types";
import { awsRegions } from "@/lib/aws-regions";
import { displayName } from "@/lib/format";
import type { RecordDraft, RecordErrors } from "@/lib/record-draft";
import {
  recordTypeInfo,
  recordTypes,
  routingPolicies,
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

const TYPE_OPTIONS = recordTypes.map(({ value, label }) => ({ value, label }));
const POLICY_OPTIONS = routingPolicies.map(({ value, label }) => ({ value, label }));

interface RecordFieldsProps {
  zoneName: string;
  draft: RecordDraft;
  errors: RecordErrors;
  onChange: (change: Partial<RecordDraft>) => void;
  /** Two columns on the create page, one in the narrow side panel. */
  columns: 1 | 2;
  /** The zone's own NS and SOA keep their name, type and routing policy. */
  identityLocked?: boolean;
}

/** The fields of one record, shared by quick create and the edit panel. */
export function RecordFields({
  zoneName,
  draft,
  errors,
  onChange,
  columns,
  identityLocked = false,
}: RecordFieldsProps) {
  const typeInfo = recordTypeInfo(draft.type);
  const typeOptions =
    draft.type === "SOA" ? [{ value: soaType.value, label: soaType.label }] : TYPE_OPTIONS;
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
      <SpaceBetween size="xs">
        <Input
          value={draft.aliasDnsName}
          placeholder="Alias target, for example d111111abcdef8.cloudfront.net"
          ariaLabel="Alias target DNS name"
          spellcheck={false}
          onChange={({ detail }) => onChange({ aliasDnsName: detail.value })}
        />
        <Input
          value={draft.aliasHostedZoneId}
          placeholder="Hosted zone ID of the target, for example Z2FDTNDATAQYW2"
          ariaLabel="Alias target hosted zone ID"
          spellcheck={false}
          onChange={({ detail }) => onChange({ aliasHostedZoneId: detail.value })}
        />
        <Toggle
          checked={draft.evaluateTargetHealth}
          onChange={({ detail }) => onChange({ evaluateTargetHealth: detail.checked })}
        >
          Evaluate target health
        </Toggle>
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
        rows={columns === 2 ? 3 : 4}
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

  const policyField = (
    <FormField label="Routing policy" info={<InfoLink topic="routing-policy" />} stretch>
      <Select
        selectedOption={
          POLICY_OPTIONS.find((option) => option.value === draft.routingPolicy) ?? null
        }
        options={POLICY_OPTIONS}
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
      <ColumnLayout columns={2}>
        {ttlField || <div />}
        {policyField}
      </ColumnLayout>
      {policyDetails}
    </SpaceBetween>
  );
}
