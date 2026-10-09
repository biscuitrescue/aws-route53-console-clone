import { Suspense } from "react";

import { Logo } from "@/components/shell/logo";
import type { PublishedCredentials } from "@/lib/api/types";
import { BACKEND_URL } from "@/lib/server/backend";

import { SignInForm } from "./sign-in-form";
import styles from "./signin.module.css";

// Rendered per request: the page carries the published credentials, so the browser does
// not have to ask for them after its scripts have loaded.
export const dynamic = "force-dynamic";

async function publishedCredentials(): Promise<PublishedCredentials | null> {
  try {
    const response = await fetch(`${BACKEND_URL}/api/v1/auth/published-credentials`, {
      cache: "no-store",
      signal: AbortSignal.timeout(2000),
    });
    return response.ok ? ((await response.json()) as PublishedCredentials) : null;
  } catch {
    // The page still works without them; sign-in itself reports an unreachable service.
    return null;
  }
}

export default async function SignInPage() {
  const published = await publishedCredentials();
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
              <SignInForm published={published} />
            </Suspense>
          </div>
          <p className={styles.legal}>
            This is a clone of the Amazon Route 53 console built for a course assignment. It is not
            affiliated with Amazon Web Services. Never enter real AWS credentials here.
          </p>
        </div>
        <section className={styles.promo} aria-label="About this clone">
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
