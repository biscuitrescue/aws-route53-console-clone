"use client";

import Alert from "@cloudscape-design/components/alert";
import Box from "@cloudscape-design/components/box";
import Button from "@cloudscape-design/components/button";
import Container from "@cloudscape-design/components/container";
import FormField from "@cloudscape-design/components/form-field";
import Header from "@cloudscape-design/components/header";
import Input from "@cloudscape-design/components/input";
import SpaceBetween from "@cloudscape-design/components/space-between";
import { useQueryClient } from "@tanstack/react-query";
import { useRouter, useSearchParams } from "next/navigation";
import { useState } from "react";
import type { FormEvent } from "react";

import { zoneListOptions } from "@/hooks/use-hosted-zones";
import { useSignIn } from "@/hooks/use-session";
import { storedPageSize } from "@/hooks/use-table-preferences";
import { useWarmUp } from "@/hooks/use-warm-up";
import { ApiError } from "@/lib/api/errors";
import { firstPage } from "@/lib/api/params";
import type { PublishedCredentials } from "@/lib/api/types";
import { routes } from "@/lib/routes";

/** Only follow redirects to pages of this app, never to another origin. */
function safeRedirect(target: string | null): string {
  return target && target.startsWith("/") && !target.startsWith("//") ? target : routes.hostedZones;
}

/** The console's frame and its landing page, fetched while the visitor is still signing in. */
const loadConsole = () =>
  Promise.all([
    import("@/components/shell/console-frame"),
    import("@/components/zones/hosted-zones-page"),
  ]);

interface SignInFormProps {
  /** Credentials the deployment publishes for visitors, if it does. */
  published: PublishedCredentials | null;
}

export function SignInForm({ published }: SignInFormProps) {
  const router = useRouter();
  const queryClient = useQueryClient();
  const searchParams = useSearchParams();
  const signIn = useSignIn();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [submitted, setSubmitted] = useState(false);

  useWarmUp(loadConsole);

  const submit = (credentials: { email: string; password: string }) => {
    signIn.mutate(credentials, {
      onSuccess: () => {
        const destination = safeRedirect(searchParams.get("redirect"));
        // Ask for the zone list now, so it arrives while the console page is being opened.
        if (destination === routes.hostedZones) {
          void queryClient.prefetchQuery(zoneListOptions(firstPage(storedPageSize("hostedZones"))));
        }
        router.replace(destination);
      },
    });
  };

  const onSubmit = (event: FormEvent) => {
    event.preventDefault();
    setSubmitted(true);
    if (email.trim() && password) submit({ email: email.trim(), password });
  };

  const failure =
    signIn.error instanceof ApiError
      ? signIn.error.message
      : signIn.error
        ? "The sign-in service is not reachable. Try again."
        : null;

  return (
    <form onSubmit={onSubmit} noValidate>
      <Container header={<Header variant="h2">Sign In</Header>}>
        <SpaceBetween size="m">
          <Box>Sign in to the Route 53 console clone.</Box>
          {failure && (
            <Alert type="error" header="There was a problem">
              {failure}
            </Alert>
          )}
          <FormField
            label="Email address"
            errorText={submitted && !email.trim() ? "Enter your email address." : undefined}
          >
            <Input
              type="email"
              inputMode="email"
              autoComplete="username"
              placeholder="username@example.com"
              value={email}
              onChange={({ detail }) => setEmail(detail.value)}
              autoFocus
            />
          </FormField>
          <FormField
            label="Password"
            errorText={submitted && !password ? "Enter your password." : undefined}
          >
            <Input
              type="password"
              autoComplete="current-password"
              value={password}
              onChange={({ detail }) => setPassword(detail.value)}
            />
          </FormField>
          <Button variant="primary" fullWidth formAction="submit" loading={signIn.isPending}>
            Sign in
          </Button>
          {published && (
            <Alert
              type="info"
              header="Sign-in credentials"
              action={
                <Button
                  formAction="none"
                  disabled={signIn.isPending}
                  onClick={() => {
                    setEmail(published.email);
                    setPassword(published.password);
                    submit(published);
                  }}
                >
                  Sign in with this account
                </Button>
              }
            >
              <Box variant="code">{published.email}</Box>
              <br />
              <Box variant="code">{published.password}</Box>
            </Alert>
          )}
        </SpaceBetween>
      </Container>
    </form>
  );
}
