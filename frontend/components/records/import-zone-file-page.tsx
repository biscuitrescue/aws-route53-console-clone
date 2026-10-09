"use client";

import { useCollection } from "@cloudscape-design/collection-hooks";
import Alert from "@cloudscape-design/components/alert";
import Box from "@cloudscape-design/components/box";
import Button from "@cloudscape-design/components/button";
import Checkbox from "@cloudscape-design/components/checkbox";
import Container from "@cloudscape-design/components/container";
import ContentLayout from "@cloudscape-design/components/content-layout";
import FileUpload from "@cloudscape-design/components/file-upload";
import Form from "@cloudscape-design/components/form";
import FormField from "@cloudscape-design/components/form-field";
import Header from "@cloudscape-design/components/header";
import Pagination from "@cloudscape-design/components/pagination";
import SpaceBetween from "@cloudscape-design/components/space-between";
import StatusIndicator from "@cloudscape-design/components/status-indicator";
import type { StatusIndicatorProps } from "@cloudscape-design/components/status-indicator";
import Table from "@cloudscape-design/components/table";
import TextFilter from "@cloudscape-design/components/text-filter";
import Textarea from "@cloudscape-design/components/textarea";
import { useQuery } from "@tanstack/react-query";
import { useRouter } from "next/navigation";
import { useState } from "react";

import { PageLoading, ZoneLoadError } from "@/components/common/page-state";
import { ConsolePage } from "@/components/shell/console-page";
import { InfoLink } from "@/components/shell/help-context";
import { useNotify } from "@/components/shell/notifications";
import { useDebouncedValue } from "@/hooks/use-debounced-value";
import { useFollow } from "@/hooks/use-follow";
import { useHostedZone } from "@/hooks/use-hosted-zones";
import { importZoneFile, useImportZoneFile } from "@/hooks/use-records";
import type { HostedZone, ImportedRecordSet } from "@/lib/api/types";
import { displayName, formatNumber } from "@/lib/format";
import { matchesText } from "@/lib/property-filter";
import { routes } from "@/lib/routes";

import { ValueLines } from "./value-lines";

const PLACEHOLDER = "subdomain1 0s A 10.0.0.0\nsubdomain2 0s CNAME example.com.";
const PREVIEW_DELAY_MS = 400;
const PREVIEW_PAGE_SIZE = 50;

const STATUS: Record<
  ImportedRecordSet["status"],
  { type: StatusIndicatorProps.Type; label: string }
> = {
  create: { type: "success", label: "Will be created" },
  replace: { type: "info", label: "Will replace existing" },
  skip: { type: "stopped", label: "Skipped" },
  error: { type: "error", label: "Error" },
};

function ImportZoneFileForm({ zone }: { zone: HostedZone }) {
  const router = useRouter();
  const follow = useFollow();
  const notify = useNotify();
  const importFile = useImportZoneFile(zone.id);
  const zoneName = displayName(zone.name);

  const [content, setContent] = useState("");
  const [files, setFiles] = useState<File[]>([]);
  const [replaceExisting, setReplaceExisting] = useState(false);
  const [submitted, setSubmitted] = useState(false);

  // The preview is a dry run of the real import, so it reports exactly what importing would do.
  const previewContent = useDebouncedValue(content, PREVIEW_DELAY_MS);
  const preview = useQuery({
    queryKey: ["zones", "detail", zone.id, "import-preview", previewContent, replaceExisting],
    queryFn: () =>
      importZoneFile(zone.id, { content: previewContent, dryRun: true, replaceExisting }),
    enabled: previewContent.trim().length > 0,
    staleTime: 0,
    retry: false,
  });

  const result = content.trim() ? preview.data : undefined;
  const recordSets = result?.record_sets ?? [];
  const [search, setSearch] = useState("");
  const term = search.trim().toLowerCase();
  const matching = term
    ? recordSets.filter((record) =>
        [record.name, record.type, ...record.values].some((text) =>
          text.toLowerCase().includes(term),
        ),
      )
    : recordSets;
  const previewTable = useCollection<ImportedRecordSet>(matching, {
    pagination: { pageSize: PREVIEW_PAGE_SIZE },
    sorting: { defaultState: { sortingColumn: { sortingField: "name" } } },
  });
  const blocked = result ? result.errors.length > 0 || (result.summary.error ?? 0) > 0 : false;
  const importable = result ? (result.summary.create ?? 0) + (result.summary.replace ?? 0) : 0;
  const emptyError = submitted && !content.trim() ? "Zone file is empty." : undefined;

  const loadFile = async (selected: File[]) => {
    setFiles(selected);
    const [file] = selected;
    if (file) setContent(await file.text());
  };

  const submit = () => {
    setSubmitted(true);
    if (!content.trim()) return;
    const done = notify.progress(`Creating record(s) for ${zoneName}`);
    importFile.mutate(
      { content, dryRun: false, replaceExisting },
      {
        onSuccess: () => {
          notify.recordsChanged(`Records for ${zoneName} were successfully created.`);
          router.push(routes.hostedZone(zone.id));
        },
        onError: notify.error,
        onSettled: done,
      },
    );
  };

  return (
    <ContentLayout
      header={
        <Header
          variant="h1"
          info={<InfoLink topic="import-zone-file" />}
          description="You can create records for a Route 53 hosted zone by importing a zone file."
        >
          Import zone file
        </Header>
      }
    >
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
              <Button
                variant="primary"
                formAction="submit"
                loading={importFile.isPending}
                disabled={blocked || (result !== undefined && importable === 0)}
              >
                Import
              </Button>
            </SpaceBetween>
          }
        >
          <SpaceBetween size="l">
            <Container
              header={
                <Header variant="h2" description="Paste the contents of your zone file below.">
                  Zone file
                </Header>
              }
            >
              <SpaceBetween size="l">
                <FormField
                  constraintText="If the hosted zone already contains records that appear in the zone file, the import process fails, and no records are created. Enter multiple records on separate lines."
                  errorText={emptyError}
                  stretch
                >
                  <Textarea
                    value={content}
                    placeholder={PLACEHOLDER}
                    rows={10}
                    spellcheck={false}
                    ariaLabel="Zone file"
                    onChange={({ detail }) => setContent(detail.value)}
                  />
                </FormField>
                <FormField
                  label="Or upload a zone file"
                  description="A text file in BIND (RFC 1035) format."
                >
                  <FileUpload
                    value={files}
                    onChange={({ detail }) => void loadFile(detail.value)}
                    accept=".zone,.txt,.db,text/plain"
                    showFileSize
                    i18nStrings={{
                      uploadButtonText: () => "Choose file",
                      dropzoneText: () => "Drop file to upload",
                      removeFileAriaLabel: (index) => `Remove file ${index + 1}`,
                      limitShowFewer: "Show fewer files",
                      limitShowMore: "Show more files",
                      errorIconAriaLabel: "Error",
                      warningIconAriaLabel: "Warning",
                    }}
                  />
                </FormField>
                <Checkbox
                  checked={replaceExisting}
                  onChange={({ detail }) => setReplaceExisting(detail.checked)}
                  description="Without this, a record that already exists in the hosted zone makes the import fail."
                >
                  Replace existing records
                </Checkbox>
              </SpaceBetween>
            </Container>

            {result && result.errors.length > 0 && (
              <Alert type="error" header="The zone file has errors">
                <ul>
                  {result.errors.map((error) => (
                    <li key={`${error.line}-${error.message}`}>
                      Line {error.line}: {error.message}
                    </li>
                  ))}
                </ul>
              </Alert>
            )}

            <Table
              {...previewTable.collectionProps}
              variant="container"
              items={previewTable.items}
              trackBy={(record) => `${record.name} ${record.type}`}
              filter={
                <TextFilter
                  filteringText={search}
                  filteringPlaceholder="Filter records by property or value"
                  filteringAriaLabel="Filter the record preview"
                  countText={term ? matchesText(matching.length) : undefined}
                  onChange={({ detail }) => setSearch(detail.filteringText)}
                />
              }
              pagination={<Pagination {...previewTable.paginationProps} />}
              loading={preview.isFetching && recordSets.length === 0}
              loadingText="Reading zone file"
              ariaLabels={{ tableLabel: "Record preview" }}
              header={
                <Header
                  variant="h2"
                  counter={`(${formatNumber(recordSets.length)})`}
                  description="Route 53 creates the following records when you choose Import zone file. If you edit the contents of the zone file above, the table reflects your changes."
                >
                  Record preview for {zoneName}
                </Header>
              }
              columnDefinitions={[
                {
                  id: "name",
                  header: "Record name",
                  sortingField: "name",
                  cell: (record) => displayName(record.name),
                  isRowHeader: true,
                },
                { id: "type", header: "Type", sortingField: "type", cell: (record) => record.type },
                {
                  id: "value",
                  header: "Value/Route traffic to",
                  sortingComparator: (a, b) => a.values.join().localeCompare(b.values.join()),
                  cell: (record) => <ValueLines values={record.values} />,
                },
                {
                  id: "ttl",
                  header: "TTL (seconds)",
                  sortingField: "ttl",
                  cell: (record) => formatNumber(record.ttl),
                },
                {
                  id: "status",
                  header: "Result",
                  sortingField: "status",
                  cell: (record) => (
                    <>
                      <StatusIndicator type={STATUS[record.status].type}>
                        {STATUS[record.status].label}
                      </StatusIndicator>
                      {record.reason && (
                        <Box color="text-body-secondary" fontSize="body-s">
                          {record.reason}
                        </Box>
                      )}
                    </>
                  ),
                },
              ]}
              empty={
                <Box textAlign="center" color="inherit" padding={{ vertical: "l" }}>
                  This table displays records based on the contents of your zone file.
                </Box>
              }
            />
          </SpaceBetween>
        </Form>
      </form>
    </ContentLayout>
  );
}

export function ImportZoneFilePage({ zoneId }: { zoneId: string }) {
  const zone = useHostedZone(zoneId);
  const name = zone.data ? displayName(zone.data.name) : "Hosted zone";
  return (
    <ConsolePage
      title={`${name} - import zone file`}
      helpTopic="import-zone-file"
      navigationOpen={false}
      breadcrumbs={[
        { text: "Hosted zones", href: routes.hostedZones },
        { text: name, href: routes.hostedZone(zoneId) },
        { text: "Import zone file", href: routes.importZoneFile(zoneId) },
      ]}
    >
      {zone.data ? (
        <ImportZoneFileForm zone={zone.data} />
      ) : zone.isError ? (
        <ZoneLoadError error={zone.error} />
      ) : (
        <PageLoading label="Loading hosted zone" />
      )}
    </ConsolePage>
  );
}
