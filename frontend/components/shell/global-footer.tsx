"use client";

import Icon from "@cloudscape-design/components/icon";

import styles from "./global-footer.module.css";

interface GlobalFooterProps {
  onShowShortcuts: () => void;
}

/** The dark bar along the bottom of every console page. */
export function GlobalFooter({ onShowShortcuts }: GlobalFooterProps) {
  return (
    <footer id="f" className={styles.footer}>
      <button type="button" className={styles.item} onClick={onShowShortcuts}>
        <Icon name="keyboard" size="small" />
        Keyboard shortcuts
      </button>
      <a
        className={`${styles.item} ${styles.optional}`}
        href="/api/docs"
        target="_blank"
        rel="noopener noreferrer"
      >
        <Icon name="script" size="small" />
        API reference
      </a>
      <span className={styles.spacer} />
      <span className={styles.optional}>
        © 2026, Route 53 console clone. A demo project, not affiliated with Amazon Web Services.
      </span>
      <a
        className={styles.item}
        href="https://cloudscape.design"
        target="_blank"
        rel="noopener noreferrer"
      >
        Built with Cloudscape
      </a>
    </footer>
  );
}
