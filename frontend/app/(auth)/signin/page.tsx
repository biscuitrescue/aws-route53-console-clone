"use client";

import Alert from "@cloudscape-design/components/alert";
import Box from "@cloudscape-design/components/box";
import Button from "@cloudscape-design/components/button";
import Container from "@cloudscape-design/components/container";
import FormField from "@cloudscape-design/components/form-field";
import Header from "@cloudscape-design/components/header";
import Input from "@cloudscape-design/components/input";
import SpaceBetween from "@cloudscape-design/components/space-between";
import { useQuery } from "@tanstack/react-query";
import { useRouter, useSearchParams } from "next/navigation";
import { Suspense, useState } from "react";
import type { FormEvent } from "react";

import { Logo } from "@/components/shell/logo";
import { useSignIn } from "@/hooks/use-session";
import { api, unwrap } from "@/lib/api/client";
import { ApiError } from "@/lib/api/errors";
import { routes } from "@/lib/routes";

import styles from "./signin.module.css";

/** Only follow redirects to pages of this app, never to another origin. */
function safeRedirect(target: string | null): string {
  return target && target.startsWith("/") && !target.startsWith("//") ? target : routes.hostedZones;
}

function SignInForm() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const signIn = useSignIn();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [submitted, setSubmitted] = useState(false);

  const demo = useQuery({
    queryKey: ["demo-credentials"],
    queryFn: () => unwrap(api.GET("/api/v1/auth/demo-credentials")),
    retry: false,
    staleTime: Infinity,
  });

  const submit = (credentials: { email: string; password: string }) => {
    signIn.mutate(credentials, {
      onSuccess: () => router.replace(safeRedirect(searchParams.get("redirect"))),
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
          <Box>Access the Route 53 console clone with the demo account.</Box>
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
          {demo.data && (
            <Alert
              type="info"
              header="Demo account"
              action={
                <Button
                  formAction="none"
                  disabled={signIn.isPending}
                  onClick={() => {
                    setEmail(demo.data.email);
                    setPassword(demo.data.password);
                    submit(demo.data);
                  }}
                >
                  Sign in as demo
                </Button>
              }
            >
              <Box variant="code">{demo.data.email}</Box>
              <br />
              <Box variant="code">{demo.data.password}</Box>
            </Alert>
          )}
        </SpaceBetween>
      </Container>
    </form>
  );
}

export default function SignInPage() {
  return (
    <main className={styles.page}>
      <div className={styles.logo}>
        <Logo width={84} smile="#ff9900" />
      </div>
      <div className={styles.columns}>
        <div>
          <div className={styles.card}>
            {/* useSearchParams needs a Suspense boundary so the page can be prerendered. */}
            <Suspense>
              <SignInForm />
            </Suspense>
          </div>
          <p className={styles.legal}>
            This is a demo clone of the Amazon Route 53 console built for a course assignment. It is
            not affiliated with Amazon Web Services. Never enter real AWS credentials here.
          </p>
        </div>
        <section className={styles.promo} aria-label="About this demo">
          <h1 className={styles.promoTitle}>Route 53 console clone</h1>
          <p className={styles.promoText}>
            Hosted zones and DNS records with the look and behaviour of the real console, on
            Next.js, FastAPI and SQLite.
          </p>
          <ul className={styles.promoList}>
            <li>Create, edit, search and delete hosted zones</li>
            <li>A, AAAA, CNAME, TXT, MX, NS, PTR, SRV and CAA records</li>
            <li>BIND zone file import, JSON and BIND export</li>
            <li>Bulk changes, dark mode and keyboard shortcuts</li>
          </ul>
        </section>
      </div>
    </main>
  );
}
