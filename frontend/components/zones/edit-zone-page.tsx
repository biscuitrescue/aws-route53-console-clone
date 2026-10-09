"use client";

import Box from "@cloudscape-design/components/box";
import Button from "@cloudscape-design/components/button";
import Container from "@cloudscape-design/components/container";
import ContentLayout from "@cloudscape-design/components/content-layout";
import Form from "@cloudscape-design/components/form";
import FormField from "@cloudscape-design/components/form-field";
import Header from "@cloudscape-design/components/header";
import SpaceBetween from "@cloudscape-design/components/space-between";
import Textarea from "@cloudscape-design/components/textarea";
import { useRouter } from "next/navigation";
import { useState } from "react";

import { PageLoading, ZoneLoadError } from "@/components/common/page-state";
import { ConsolePage } from "@/components/shell/console-page";
import { InfoLink } from "@/components/shell/help-context";
import { useNotify } from "@/components/shell/notifications";
import { useFollow } from "@/hooks/use-follow";
import { useHostedZone, useUpdateHostedZone } from "@/hooks/use-hosted-zones";
import type { HostedZone, VpcAssociation } from "@/lib/api/types";
import { displayName, formatNumber, zoneTypeLongLabel } from "@/lib/format";
import { routes } from "@/lib/routes";

import { DESCRIPTION_LIMIT } from "./create-zone-page";
import { TagsContainer, toApiTags, toEditableTags } from "./tags-container";
import type { EditableTag } from "./tags-container";
import { toApiVpcs, vpcsComplete, VpcsContainer } from "./vpcs-container";

function EditZoneForm({ zone }: { zone: HostedZone }) {
  const router = useRouter();
  const follow = useFollow();
  const notify = useNotify();
  const updateZone = useUpdateHostedZone(zone.id);
  const name = displayName(zone.name);
  const isPrivate = zone.type === "private";

  const [description, setDescription] = useState(zone.description);
  const [tags, setTags] = useState<readonly EditableTag[]>(() => toEditableTags(zone.tags));
  const [vpcs, setVpcs] = useState<VpcAssociation[]>(zone.vpcs);
  const [submitted, setSubmitted] = useState(false);

  const submit = () => {
    setSubmitted(true);
    if (isPrivate && !vpcsComplete(vpcs)) return;
    updateZone.mutate(
      { description, tags: toApiTags(tags), ...(isPrivate && { vpcs: toApiVpcs(vpcs) }) },
      {
        onSuccess: () => {
          notify.success(`Hosted zone ${name} was successfully updated.`);
          router.push(routes.hostedZone(zone.id));
        },
        onError: notify.error,
      },
    );
  };

  const facts = [
    { label: "Domain name", value: name },
    { label: "Hosted zone ID", value: zone.id },
    { label: "Record count", value: formatNumber(zone.record_count) },
    { label: "Type", value: zoneTypeLongLabel[zone.type] },
  ];

  return (
    <ContentLayout
      header={
        <Header variant="h1" info={<InfoLink topic="hosted-zones" />}>
          Edit {name}
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
              <Button variant="primary" formAction="submit" loading={updateZone.isPending}>
                Save changes
              </Button>
            </SpaceBetween>
          }
        >
          <SpaceBetween size="l">
            <Container
              header={
                <Header
                  variant="h2"
                  description="A hosted zone is a container that holds information about how you want to route traffic for a domain, such as example.com, and its subdomains."
                >
                  Edit hosted zone
                </Header>
              }
            >
              <SpaceBetween size="l">
                {facts.map((fact) => (
                  <div key={fact.label}>
                    <Box variant="awsui-key-label">{fact.label}</Box>
                    <div>{fact.value}</div>
                  </div>
                ))}
                <FormField
                  label={
                    <>
                      Description - <i>optional</i>
                    </>
                  }
                  info={<InfoLink topic="description" />}
                  description="This value lets you distinguish hosted zones that have the same name."
                  constraintText={`The description can have up to ${DESCRIPTION_LIMIT} characters. ${description.length}/${DESCRIPTION_LIMIT}`}
                >
                  <Textarea
                    value={description}
                    placeholder="The hosted zone is used for..."
                    onChange={({ detail }) =>
                      setDescription(detail.value.slice(0, DESCRIPTION_LIMIT))
                    }
                  />
                </FormField>
              </SpaceBetween>
            </Container>
            {isPrivate && <VpcsContainer vpcs={vpcs} onChange={setVpcs} showErrors={submitted} />}
            <TagsContainer tags={tags} onChange={setTags} />
          </SpaceBetween>
        </Form>
      </form>
    </ContentLayout>
  );
}

export function EditZonePage({ zoneId }: { zoneId: string }) {
  const zone = useHostedZone(zoneId);
  const name = zone.data ? displayName(zone.data.name) : "Hosted zone";
  return (
    <ConsolePage
      title={`${name} - edit`}
      helpTopic="hosted-zones"
      navigationOpen={false}
      breadcrumbs={[
        { text: "Hosted zones", href: routes.hostedZones },
        { text: name, href: routes.hostedZone(zoneId) },
        { text: "Edit", href: routes.editHostedZone(zoneId) },
      ]}
    >
      {zone.data ? (
        <EditZoneForm zone={zone.data} />
      ) : zone.isError ? (
        <ZoneLoadError error={zone.error} />
      ) : (
        <PageLoading label="Loading hosted zone" />
      )}
    </ConsolePage>
  );
}
