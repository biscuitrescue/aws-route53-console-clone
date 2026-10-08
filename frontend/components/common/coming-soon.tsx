"use client";

import Box from "@cloudscape-design/components/box";
import Button from "@cloudscape-design/components/button";
import Container from "@cloudscape-design/components/container";
import ContentLayout from "@cloudscape-design/components/content-layout";
import Header from "@cloudscape-design/components/header";
import SpaceBetween from "@cloudscape-design/components/space-between";

import { ConsolePage } from "@/components/shell/console-page";
import { InfoLink } from "@/components/shell/help-context";
import { useFollow } from "@/hooks/use-follow";
import { placeholderHref } from "@/lib/navigation";
import type { PlaceholderSection } from "@/lib/navigation";
import { routes } from "@/lib/routes";

/** A console section that exists in the navigation but is outside the clone's scope. */
export function ComingSoon({ section }: { section: PlaceholderSection }) {
  const follow = useFollow();
  const href = placeholderHref(section);
  return (
    <ConsolePage
      title={`${section.title} | Route 53`}
      helpTopic="coming-soon"
      breadcrumbs={[
        ...(section.group ? [{ text: section.group, href }] : []),
        { text: section.title, href },
      ]}
    >
      <ContentLayout
        header={
          <Header
            variant="h1"
            info={<InfoLink topic="coming-soon" />}
            description={section.description}
          >
            {section.title}
          </Header>
        }
      >
        <Container>
          <Box textAlign="center" padding={{ vertical: "xxxl" }}>
            <SpaceBetween size="m">
              <Box variant="h2">Coming soon</Box>
              <Box color="text-body-secondary">
                {section.title} is not part of this clone yet. Hosted zones and records are fully
                functional.
              </Box>
              <Button variant="primary" href={routes.hostedZones} onFollow={follow}>
                Go to hosted zones
              </Button>
            </SpaceBetween>
          </Box>
        </Container>
      </ContentLayout>
    </ConsolePage>
  );
}
