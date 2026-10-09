"use client";

import Box from "@cloudscape-design/components/box";
import Button from "@cloudscape-design/components/button";
import Container from "@cloudscape-design/components/container";
import Header from "@cloudscape-design/components/header";
import Modal from "@cloudscape-design/components/modal";
import SpaceBetween from "@cloudscape-design/components/space-between";
import Table from "@cloudscape-design/components/table";
import Tiles from "@cloudscape-design/components/tiles";
import Wizard from "@cloudscape-design/components/wizard";
import { useRouter } from "next/navigation";
import { useState } from "react";

import { InfoLink } from "@/components/shell/help-context";
import { useNotify } from "@/components/shell/notifications";
import { useChangeRecords } from "@/hooks/use-records";
import type { HostedZone, RoutingPolicy } from "@/lib/api/types";
import { displayName } from "@/lib/format";
import {
  createdRecordsHeader,
  draftToInput,
  emptyDraft,
  hasErrors,
  validateDraft,
} from "@/lib/record-draft";
import type { RecordDraft, RecordErrors } from "@/lib/record-draft";
import { routes } from "@/lib/routes";

import { ExistingRecords } from "./existing-records";
import { RecordFields } from "./record-fields";

interface PolicyChoice {
  value: RoutingPolicy | "ip-based" | "geoproximity";
  label: string;
  /** The word used in "Define … record". */
  noun: string;
  description: string;
  supported: boolean;
}

/** The routing policies of step 1, with the console's descriptions. */
const POLICIES: PolicyChoice[] = [
  {
    value: "simple",
    label: "Simple routing",
    noun: "simple",
    description: "Use if you want all of your clients to receive the same response(s).",
    supported: true,
  },
  {
    value: "weighted",
    label: "Weighted",
    noun: "weighted",
    description:
      "Use when you have multiple resources that do the same job, and you want to specify the proportion of traffic that goes to each resource. For example: two or more EC2 instances.",
    supported: true,
  },
  {
    value: "geolocation",
    label: "Geolocation",
    noun: "geolocation",
    description: "Use when you want to route traffic based on the location of your users.",
    supported: true,
  },
  {
    value: "latency",
    label: "Latency",
    noun: "latency",
    description:
      "Use when you have resources in multiple AWS Regions and you want to route traffic to the Region that provides the best latency.",
    supported: true,
  },
  {
    value: "failover",
    label: "Failover",
    noun: "failover",
    description:
      "Use to route traffic to a resource when the resource is healthy, or to a different resource when the first resource is unhealthy.",
    supported: true,
  },
  {
    value: "multivalue",
    label: "Multivalue answer",
    noun: "multivalue answer",
    description:
      "Use when you want Route 53 to respond to DNS queries with up to eight healthy records selected at random.",
    supported: true,
  },
  {
    value: "ip-based",
    label: "IP-based",
    noun: "IP-based",
    description: "Use to route traffic to locations of IP address ranges in CIDR notation.",
    supported: false,
  },
  {
    value: "geoproximity",
    label: "Geoproximity",
    noun: "geoproximity",
    description:
      "Use when you want Route 53 to route DNS queries to a certain geographic location.",
    supported: false,
  },
];

function draftTargets(draft: RecordDraft): string[] {
  return draft.alias ? [draft.aliasDnsName] : draft.values.split("\n").filter(Boolean);
}

interface RecordWizardProps {
  zone: HostedZone;
  onSwitchToQuickCreate: () => void;
}

/** The two-step way of creating records: choose a routing policy, then define records for it. */
export function RecordWizard({ zone, onSwitchToQuickCreate }: RecordWizardProps) {
  const router = useRouter();
  const notify = useNotify();
  const changeRecords = useChangeRecords(zone.id);
  const zoneName = displayName(zone.name);

  const [step, setStep] = useState(0);
  const [policy, setPolicy] = useState<RoutingPolicy>("simple");
  const [drafts, setDrafts] = useState<RecordDraft[]>([]);
  const [selected, setSelected] = useState<RecordDraft[]>([]);
  // The record in the "Define record" dialog: a new one or a copy of one being edited.
  const [defining, setDefining] = useState<RecordDraft | null>(null);
  const [errors, setErrors] = useState<RecordErrors>({});
  const [submitted, setSubmitted] = useState(false);

  const choice = POLICIES.find((candidate) => candidate.value === policy) ?? POLICIES[0];
  const defineLabel = `Define ${choice.noun} record`;

  const choosePolicy = (next: RoutingPolicy) => {
    setPolicy(next);
    // Records defined for another policy would no longer be valid.
    setDrafts([]);
    setSelected([]);
  };

  const changeDefining = (update: Partial<RecordDraft>) => {
    if (!defining) return;
    const next = { ...defining, ...update };
    setDefining(next);
    if (hasErrors(errors)) setErrors(validateDraft(next));
  };

  const closeDialog = () => {
    setDefining(null);
    setErrors({});
  };

  const confirmDefining = () => {
    if (!defining) return;
    const found = validateDraft(defining);
    setErrors(found);
    if (hasErrors(found)) return;
    setDrafts((current) =>
      current.some((draft) => draft.key === defining.key)
        ? current.map((draft) => (draft.key === defining.key ? defining : draft))
        : [...current, defining],
    );
    setSelected([]);
    closeDialog();
  };

  const submit = () => {
    setSubmitted(true);
    if (drafts.length === 0) return;
    const done = notify.progress(`Creating record(s) for ${zoneName}`);
    changeRecords.mutate(
      drafts.map((draft) => ({ action: "CREATE" as const, record_set: draftToInput(draft) })),
      {
        onSuccess: (result) => {
          notify.recordsChanged(createdRecordsHeader(result, zoneName), result.id);
          router.push(routes.hostedZone(zone.id));
        },
        onError: notify.error,
        onSettled: done,
      },
    );
  };

  return (
    <>
      <Wizard
        activeStepIndex={step}
        onNavigate={({ detail }) => setStep(detail.requestedStepIndex)}
        onCancel={() => router.push(routes.hostedZone(zone.id))}
        onSubmit={submit}
        isLoadingNextStep={changeRecords.isPending}
        i18nStrings={{
          stepNumberLabel: (number) => `Step ${number}`,
          collapsedStepsLabel: (number, count) => `Step ${number} of ${count}`,
          navigationAriaLabel: "Steps",
          cancelButton: "Cancel",
          previousButton: "Previous",
          nextButton: "Next",
          submitButton: "Create records",
        }}
        steps={[
          {
            title: "Choose routing policy",
            info: <InfoLink topic="routing-policy" />,
            description: "The routing policy determines how Amazon Route 53 responds to queries.",
            content: (
              <Container
                header={
                  <Header
                    variant="h2"
                    actions={
                      <Button variant="inline-link" onClick={onSwitchToQuickCreate}>
                        Switch to quick create
                      </Button>
                    }
                  >
                    Routing policy
                  </Header>
                }
              >
                <Tiles
                  columns={2}
                  ariaLabel="Routing policy"
                  value={policy}
                  onChange={({ detail }) => choosePolicy(detail.value as RoutingPolicy)}
                  items={POLICIES.map(({ value, label, description, supported }) => ({
                    value,
                    label,
                    description: supported
                      ? description
                      : `${description} Not supported in this clone.`,
                    disabled: !supported,
                  }))}
                />
              </Container>
            ),
          },
          {
            title: "Configure records",
            info: <InfoLink topic="create-record" />,
            description:
              "You can create multiple records at a time that have the same routing policy.",
            errorText:
              submitted && drafts.length === 0
                ? `Define at least one ${choice.noun} record.`
                : undefined,
            content: (
              <SpaceBetween size="l">
                <Table
                  variant="container"
                  items={drafts}
                  trackBy="key"
                  selectionType="multi"
                  selectedItems={selected}
                  onSelectionChange={({ detail }) => setSelected(detail.selectedItems)}
                  ariaLabels={{
                    tableLabel: "Records to add",
                    selectionGroupLabel: "Records selection",
                    allItemsSelectionLabel: () => "Select all records",
                    itemSelectionLabel: (_data, draft) => `Select record ${draft.name || zoneName}`,
                  }}
                  header={
                    <Header
                      variant="h2"
                      info={<InfoLink topic="routing-policy" />}
                      description={choice.description}
                      actions={
                        <SpaceBetween direction="horizontal" size="xs">
                          <Button
                            disabled={selected.length !== 1}
                            onClick={() => setDefining(selected[0])}
                          >
                            Edit
                          </Button>
                          <Button
                            disabled={selected.length === 0}
                            onClick={() => {
                              const removed = new Set(selected.map((draft) => draft.key));
                              setDrafts((current) =>
                                current.filter((draft) => !removed.has(draft.key)),
                              );
                              setSelected([]);
                            }}
                          >
                            Delete
                          </Button>
                          <Button
                            onClick={() => setDefining({ ...emptyDraft(), routingPolicy: policy })}
                          >
                            {defineLabel}
                          </Button>
                        </SpaceBetween>
                      }
                    >
                      {choice.label} records to add to {zoneName}
                    </Header>
                  }
                  columnDefinitions={[
                    {
                      id: "name",
                      header: "Record name",
                      isRowHeader: true,
                      cell: (draft) =>
                        draft.name.trim() ? `${draft.name.trim()}.${zoneName}` : zoneName,
                    },
                    { id: "type", header: "Type", cell: (draft) => draft.type },
                    {
                      id: "value",
                      header: "Value/Route traffic to",
                      cell: (draft) =>
                        draftTargets(draft).map((target) => <div key={target}>{target}</div>),
                    },
                    {
                      id: "ttl",
                      header: "TTL (seconds)",
                      cell: (draft) => (draft.alias ? "-" : draft.ttl),
                    },
                  ]}
                  empty={
                    <Box textAlign="center" color="inherit" padding={{ vertical: "s" }}>
                      <SpaceBetween size="s">
                        <Box color="inherit">
                          Define {choice.noun} records to this list, then choose{" "}
                          <b>Create records</b>.
                        </Box>
                        <Button
                          onClick={() => setDefining({ ...emptyDraft(), routingPolicy: policy })}
                        >
                          {defineLabel}
                        </Button>
                      </SpaceBetween>
                    </Box>
                  }
                />
                <ExistingRecords zone={zone} title="Existing records" />
              </SpaceBetween>
            ),
          },
        ]}
      />
      {defining && (
        <Modal
          visible
          onDismiss={closeDialog}
          header={defineLabel}
          closeAriaLabel="Close modal"
          footer={
            <Box float="right">
              <SpaceBetween direction="horizontal" size="xs">
                <Button variant="link" onClick={closeDialog}>
                  Cancel
                </Button>
                <Button variant="primary" onClick={confirmDefining}>
                  {defineLabel}
                </Button>
              </SpaceBetween>
            </Box>
          }
        >
          <RecordFields
            zone={zone}
            draft={defining}
            errors={errors}
            onChange={changeDefining}
            columns={1}
            policyFixed
            autoFocus
          />
        </Modal>
      )}
    </>
  );
}
