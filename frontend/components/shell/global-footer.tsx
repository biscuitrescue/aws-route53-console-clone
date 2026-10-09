"use client";

import Box from "@cloudscape-design/components/box";
import Button from "@cloudscape-design/components/button";
import Modal from "@cloudscape-design/components/modal";
import SpaceBetween from "@cloudscape-design/components/space-between";
import { useState } from "react";

import styles from "./global-footer.module.css";
import { AgentToolkitGlyph, CloudShellGlyph } from "./header-icons";
import { useNotify } from "./notifications";

const REPOSITORY = "https://github.com/biscuitrescue/aws-route53-console-clone";

/** What the footer's legal links say in a demo that has no legal department. */
function AboutModal({ onDismiss }: { onDismiss: () => void }) {
  return (
    <Modal
      visible
      onDismiss={onDismiss}
      header="About this demo"
      footer={
        <Box float="right">
          <Button variant="primary" onClick={onDismiss}>
            Close
          </Button>
        </Box>
      }
    >
      <SpaceBetween size="m">
        <Box variant="p">
          This is a clone of the Amazon Route 53 console built for a course assignment. It is not
          affiliated with Amazon Web Services and serves no DNS.
        </Box>
        <div>
          <Box variant="h3">Privacy</Box>
          <Box variant="p">
            The only account is a shared demo account. Hosted zones and records you create are
            visible to everyone who signs in. Do not enter personal data or real credentials.
          </Box>
        </div>
        <div>
          <Box variant="h3">Terms</Box>
          <Box variant="p">
            The demo is provided as is, without any guarantee of availability, and its data may be
            reset at any time.
          </Box>
        </div>
        <div>
          <Box variant="h3">Cookie preferences</Box>
          <Box variant="p">
            One essential cookie keeps you signed in; it cannot be read by scripts. Table, panel and
            visual mode preferences are kept in this browser&apos;s local storage. There are no
            analytics or advertising cookies, so there is nothing to opt out of.
          </Box>
        </div>
      </SpaceBetween>
    </Modal>
  );
}

/** The dark bar along the bottom of every console page. */
export function GlobalFooter() {
  const notify = useNotify();
  const [aboutVisible, setAboutVisible] = useState(false);

  const notAvailable = (feature: string, detail: string) => () =>
    notify.info(`${feature} is not available in this demo`, detail);
  const about = () => setAboutVisible(true);

  return (
    <footer id="f" className={styles.footer}>
      <button
        type="button"
        className={styles.item}
        title="Open CloudShell"
        onClick={notAvailable(
          "CloudShell",
          "This clone has no shell. Its REST API is documented at /api/docs.",
        )}
      >
        <CloudShellGlyph />
        CloudShell
      </button>
      <button
        type="button"
        className={`${styles.item} ${styles.optional}`}
        onClick={notAvailable(
          "Agent Toolkit for AWS",
          "The toolkit belongs to the AWS console and is not part of this clone.",
        )}
      >
        <AgentToolkitGlyph />
        Agent Toolkit for AWS
      </button>
      <a
        className={`${styles.item} ${styles.optional}`}
        href={`${REPOSITORY}/issues`}
        target="_blank"
        rel="noopener noreferrer"
        title="Feedback"
      >
        Feedback
      </a>
      <button
        type="button"
        className={`${styles.item} ${styles.optional}`}
        title="Language"
        onClick={notAvailable("Language", "This clone is available in English only.")}
      >
        Language
      </button>
      <span className={styles.spacer} />
      <span className={styles.copyright}>
        © 2026, Route 53 console clone. Not affiliated with Amazon Web Services.
      </span>
      <button type="button" className={styles.item} title="Privacy" onClick={about}>
        Privacy
      </button>
      <button type="button" className={styles.item} title="Terms" onClick={about}>
        Terms
      </button>
      <button type="button" className={styles.item} title="Cookie preferences" onClick={about}>
        Cookie preferences
      </button>
      {aboutVisible && <AboutModal onDismiss={() => setAboutVisible(false)} />}
    </footer>
  );
}
