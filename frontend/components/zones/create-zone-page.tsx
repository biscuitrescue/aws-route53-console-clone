"use client";

import Button from "@cloudscape-design/components/button";
import Container from "@cloudscape-design/components/container";
import ContentLayout from "@cloudscape-design/components/content-layout";
import Form from "@cloudscape-design/components/form";
import FormField from "@cloudscape-design/components/form-field";
import Header from "@cloudscape-design/components/header";
import Input from "@cloudscape-design/components/input";
import SpaceBetween from "@cloudscape-design/components/space-between";
import Textarea from "@cloudscape-design/components/textarea";
import Tiles from "@cloudscape-design/components/tiles";
import { useRouter } from "next/navigation";
import { useState } from "react";

import { ConsolePage } from "@/components/shell/console-page";
import { InfoLink } from "@/components/shell/help-context";
import { useNotify } from "@/components/shell/notifications";
import { useFollow } from "@/hooks/use-follow";
import { useCreateHostedZone } from "@/hooks/use-hosted-zones";
import type { VpcAssociation, ZoneType } from "@/lib/api/types";
import { displayName } from "@/lib/format";
import { routes } from "@/lib/routes";

import { TagsContainer, toApiTags } from "./tags-container";
import type { EditableTag } from "./tags-container";
import { EMPTY_VPC, toApiVpcs, vpcsComplete, VpcsContainer } from "./vpcs-container";

export const DESCRIPTION_LIMIT = 256;
const VALID_CHARACTERS =
  "Valid characters: a-z, 0-9, ! \" # $ % & ' ( ) * + , - / : ; < = > ? @ [ \\ ] ^ _ ` { | } . ~";

export function CreateZonePage() {
  const router = useRouter();
  const follow = useFollow();
  const notify = useNotify();
  const createZone = useCreateHostedZone();

  const [name, setName] = useState("");
  const [description, setDescription] = useState("");
  const [type, setType] = useState<ZoneType>("public");
  const [vpcs, setVpcs] = useState<VpcAssociation[]>([EMPTY_VPC]);
  const [tags, setTags] = useState<readonly EditableTag[]>([]);
  const [submitted, setSubmitted] = useState(false);

  const nameError = submitted && !name.trim() ? "Domain name is empty." : undefined;
  const vpcsIncomplete = type === "private" && !vpcsComplete(vpcs);

  const submit = () => {
    setSubmitted(true);
    if (!name.trim() || vpcsIncomplete) return;
    const done = notify.progress(`Creating hosted zone ${name.trim()}`);
    createZone.mutate(
      {
        name: name.trim(),
        description,
        type,
        vpcs: type === "private" ? toApiVpcs(vpcs) : [],
        tags: toApiTags(tags),
      },
      {
        onSuccess: (zone) => {
          notify.success(
            `${displayName(zone.name)} was successfully created.`,
            "Now you can create records in the hosted zone to specify how you want Route 53 to route traffic for your domain.",
          );
          router.push(routes.hostedZone(zone.id));
        },
        onError: notify.error,
        onSettled: done,
      },
    );
  };

  return (
    <ConsolePage
      title="Create hosted zone | Route 53"
      helpTopic="create-hosted-zone"
      navigationOpen={false}
      breadcrumbs={[
        { text: "Hosted zones", href: routes.hostedZones },
        { text: "Create hosted zone", href: routes.createHostedZone },
      ]}
    >
      <ContentLayout
        header={
          <Header variant="h1" info={<InfoLink topic="create-hosted-zone" />}>
            Create hosted zone
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
                  href={routes.hostedZones}
                  onFollow={follow}
                  formAction="none"
                >
                  Cancel
                </Button>
                <Button variant="primary" formAction="submit" loading={createZone.isPending}>
                  Create hosted zone
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
                    Hosted zone configuration
                  </Header>
                }
              >
                <SpaceBetween size="l">
                  <FormField
                    label="Domain name"
                    info={<InfoLink topic="domain-name" />}
                    description="This is the name of the domain that you want to route traffic for."
                    constraintText={VALID_CHARACTERS}
                    errorText={nameError}
                  >
                    <Input
                      value={name}
                      placeholder="example.com"
                      onChange={({ detail }) => setName(detail.value)}
                      autoFocus
                      spellcheck={false}
                    />
                  </FormField>
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
                  <FormField
                    label="Type"
                    info={<InfoLink topic="zone-type" />}
                    description="The type indicates whether you want to route traffic on the internet or in an Amazon VPC."
                  >
                    <Tiles
                      value={type}
                      onChange={({ detail }) => setType(detail.value as ZoneType)}
                      items={[
                        {
                          value: "public",
                          label: "Public hosted zone",
                          description:
                            "A public hosted zone determines how traffic is routed on the internet.",
                        },
                        {
                          value: "private",
                          label: "Private hosted zone",
                          description:
                            "A private hosted zone determines how traffic is routed within an Amazon VPC.",
                        },
                      ]}
                    />
                  </FormField>
                </SpaceBetween>
              </Container>

              {type === "private" && (
                <VpcsContainer vpcs={vpcs} onChange={setVpcs} showErrors={submitted} />
              )}

              <TagsContainer tags={tags} onChange={setTags} />
            </SpaceBetween>
          </Form>
        </form>
      </ContentLayout>
    </ConsolePage>
  );
}
