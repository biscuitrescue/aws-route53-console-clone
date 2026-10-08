"use client";

import Alert from "@cloudscape-design/components/alert";
import Box from "@cloudscape-design/components/box";
import Button from "@cloudscape-design/components/button";
import Spinner from "@cloudscape-design/components/spinner";

import { useFollow } from "@/hooks/use-follow";
import { ApiError } from "@/lib/api/errors";
import { routes } from "@/lib/routes";

/** Centered spinner while a page's main resource loads. */
export function PageLoading({ label }: { label: string }) {
  return (
    <Box textAlign="center" padding={{ vertical: "xxxl" }}>
      <Spinner size="large" /> <Box variant="span">{label}</Box>
    </Box>
  );
}

/** Shown instead of a page when its hosted zone cannot be loaded. */
export function ZoneLoadError({ error }: { error: unknown }) {
  const follow = useFollow();
  const missing = error instanceof ApiError && error.status === 404;
  return (
    <Alert
      type="error"
      header={missing ? "Hosted zone not found" : "The hosted zone could not be loaded"}
      action={
        <Button href={routes.hostedZones} onFollow={follow}>
          View hosted zones
        </Button>
      }
    >
      {error instanceof Error ? error.message : "Try again."}
    </Alert>
  );
}
