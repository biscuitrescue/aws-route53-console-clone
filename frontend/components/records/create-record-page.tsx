"use client";

import Box from "@cloudscape-design/components/box";
import Button from "@cloudscape-design/components/button";
import ColumnLayout from "@cloudscape-design/components/column-layout";
import Container from "@cloudscape-design/components/container";
import ContentLayout from "@cloudscape-design/components/content-layout";
import ExpandableSection from "@cloudscape-design/components/expandable-section";
import Form from "@cloudscape-design/components/form";
import Header from "@cloudscape-design/components/header";
import SpaceBetween from "@cloudscape-design/components/space-between";
import { useRouter } from "next/navigation";
import { useEffect, useState } from "react";

import { PageLoading, ZoneLoadError } from "@/components/common/page-state";
import { ConsolePage } from "@/components/shell/console-page";
import { InfoLink } from "@/components/shell/help-context";
import { useNotify } from "@/components/shell/notifications";
import { useFollow } from "@/hooks/use-follow";
import { useHostedZone } from "@/hooks/use-hosted-zones";
import { usePersistedState } from "@/hooks/use-persisted-state";
import { useChangeRecords } from "@/hooks/use-records";
import type { HostedZone } from "@/lib/api/types";
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
import { RecordWizard } from "./record-wizard";

function CreateRecordForm({ zone }: { zone: HostedZone }) {
  const router = useRouter();
  const follow = useFollow();
  const notify = useNotify();
  const changeRecords = useChangeRecords(zone.id);
  const zoneName = displayName(zone.name);

  const [drafts, setDrafts] = useState<RecordDraft[]>(() => [emptyDraft()]);
  // The record whose name field takes focus: the first on arrival, then each one added.
  const [focusKey, setFocusKey] = useState(() => drafts[0].key);
  const [errors, setErrors] = useState<Record<string, RecordErrors>>({});
  const [submitted, setSubmitted] = useState(false);
  const [mode, setMode] = useState<"quick" | "wizard">("quick");

  // The console explains the two creation methods on the first visit only.
  const [methodsSeen, setMethodsSeen] = usePersistedState("createRecord.methodsSeen", false);
  const [explainMethods] = useState(!methodsSeen);
  useEffect(() => setMethodsSeen(true), [setMethodsSeen]);

  const validateAll = (candidates: RecordDraft[]) =>
    Object.fromEntries(candidates.map((draft) => [draft.key, validateDraft(draft)]));

  const change = (key: string, update: Partial<RecordDraft>) => {
    const next = drafts.map((draft) => (draft.key === key ? { ...draft, ...update } : draft));
    setDrafts(next);
    // Validate on submit first, then live, as the console does.
    if (submitted) setErrors(validateAll(next));
  };

  const submit = () => {
    const found = validateAll(drafts);
    setSubmitted(true);
    setErrors(found);
    if (Object.values(found).some(hasErrors)) return;
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

  if (mode === "wizard") {
    return <RecordWizard zone={zone} onSwitchToQuickCreate={() => setMode("quick")} />;
  }

  return (
    <SpaceBetween size="l">
      {explainMethods && (
        <ExpandableSection variant="container" headerText="Record creation method" defaultExpanded>
          <ColumnLayout columns={2}>
            <div>
              <Box variant="h4">Quick create (recommended for expert users)</Box>
              <Box variant="p">
                Choose this method if you are confident in the process of creating records and know
                which options you need.
              </Box>
            </div>
            <div>
              <Box variant="h4">Wizard (recommended for new users)</Box>
              <Box variant="p">
                Choose this method if you need more explanations as you create your record.
              </Box>
            </div>
          </ColumnLayout>
        </ExpandableSection>
      )}

      <ContentLayout
        header={
          <Header variant="h1" info={<InfoLink topic="create-record" />}>
            Create record
          </Header>
        }
      >
        <SpaceBetween size="l">
          <form
            onSubmit={(event) => {
              event.preventDefault();
              submit();
            }}
            noValidate
          >
            <Form
              actions={
                <SpaceBetween direction="horizontal" size="xs">
                  <Button
                    variant="link"
                    href={routes.hostedZone(zone.id)}
                    onFollow={follow}
                    formAction="none"
                  >
                    Cancel
                  </Button>
                  <Button variant="primary" formAction="submit" loading={changeRecords.isPending}>
                    Create records
                  </Button>
                </SpaceBetween>
              }
            >
              <Container
                header={
                  <Header
                    variant="h2"
                    actions={
                      <Button
                        variant="inline-link"
                        formAction="none"
                        onClick={() => setMode("wizard")}
                      >
                        Switch to wizard
                      </Button>
                    }
                  >
                    Quick create record
                  </Header>
                }
                footer={
                  <Box float="right">
                    <Button
                      formAction="none"
                      onClick={() => {
                        const added = emptyDraft();
                        setDrafts((current) => [...current, added]);
                        setFocusKey(added.key);
                      }}
                    >
                      Add another record
                    </Button>
                  </Box>
                }
              >
                <ColumnLayout borders="horizontal">
                  {drafts.map((draft, index) => (
                    <div key={draft.key} data-record-index={index}>
                      <ExpandableSection
                        defaultExpanded
                        headerText={
                          <Box variant="span" fontSize="body-m" fontWeight="bold">
                            Record {index + 1}
                          </Box>
                        }
                        headerActions={
                          <Button
                            formAction="none"
                            disabled={drafts.length === 1}
                            ariaLabel={`Delete record ${index + 1}`}
                            onClick={() =>
                              setDrafts((current) =>
                                current.filter((item) => item.key !== draft.key),
                              )
                            }
                          >
                            Delete
                          </Button>
                        }
                      >
                        <RecordFields
                          zone={zone}
                          draft={draft}
                          errors={errors[draft.key] ?? {}}
                          onChange={(update) => change(draft.key, update)}
                          columns={2}
                          autoFocus={draft.key === focusKey}
                        />
                      </ExpandableSection>
                    </div>
                  ))}
                </ColumnLayout>
              </Container>
            </Form>
          </form>
          <ExistingRecords zone={zone} />
        </SpaceBetween>
      </ContentLayout>
    </SpaceBetween>
  );
}

export function CreateRecordPage({ zoneId }: { zoneId: string }) {
  const zone = useHostedZone(zoneId);
  const name = zone.data ? displayName(zone.data.name) : "Hosted zone";
  return (
    <ConsolePage
      title={`${name} - add record`}
      helpTopic="create-record"
      navigationOpen={false}
      breadcrumbs={[
        { text: "Hosted zones", href: routes.hostedZones },
        { text: name, href: routes.hostedZone(zoneId) },
        { text: "Create record", href: routes.createRecord(zoneId) },
      ]}
    >
      {zone.data ? (
        <CreateRecordForm zone={zone.data} />
      ) : zone.isError ? (
        <ZoneLoadError error={zone.error} />
      ) : (
        <PageLoading label="Loading hosted zone" />
      )}
    </ConsolePage>
  );
}
