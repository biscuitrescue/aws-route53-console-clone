"use client";

import Icon from "@cloudscape-design/components/icon";
import { useRouter } from "next/navigation";
import { useEffect, useRef, useState } from "react";
import type { FormEvent } from "react";

import { useDebouncedValue } from "@/hooks/use-debounced-value";
import { useHostedZones } from "@/hooks/use-hosted-zones";
import { displayName } from "@/lib/format";
import { routes } from "@/lib/routes";

import styles from "./global-header.module.css";
import { AssistantGlyph, AssistantTile } from "./header-icons";
import { AccountMenu, HelpMenu, NotificationsMenu, ServicesMenu } from "./header-menus";
import { Logo } from "./logo";
import { useNotify } from "./notifications";

const ASSISTANT_NOTE =
  "The assistant belongs to the AWS console and is not part of this clone. Use the search field to find hosted zones.";
const SEARCH_RESULTS = 6;

/** The search field of the navigation bar: finds hosted zones by name, description or ID. */
function Search({ onAskAssistant }: { onAskAssistant: () => void }) {
  const router = useRouter();
  const form = useRef<HTMLFormElement>(null);
  const input = useRef<HTMLInputElement>(null);
  const [term, setTerm] = useState("");
  const [focused, setFocused] = useState(false);
  // On narrow screens the field is folded into a button and opens over the bar.
  const [unfolded, setUnfolded] = useState(false);

  const query = useDebouncedValue(term.trim(), 200);
  const results = useHostedZones(
    { search: query, page: 1, pageSize: SEARCH_RESULTS },
    { enabled: focused && query !== "" },
  );
  const showResults = focused && query !== "" && term.trim() !== "";

  // Alt+S focuses the search field, as in the console.
  useEffect(() => {
    const onKeyDown = (event: KeyboardEvent) => {
      if (event.altKey && event.code === "KeyS") {
        event.preventDefault();
        input.current?.focus();
      }
    };
    document.addEventListener("keydown", onKeyDown);
    return () => document.removeEventListener("keydown", onKeyDown);
  }, []);

  const leave = (href: string) => {
    setTerm("");
    setFocused(false);
    input.current?.blur();
    router.push(href);
  };

  const submit = (event: FormEvent) => {
    event.preventDefault();
    const text = term.trim();
    leave(text ? `${routes.hostedZones}?search=${encodeURIComponent(text)}` : routes.hostedZones);
  };

  return (
    <>
      <button
        type="button"
        className={`${styles.iconButton} ${styles.searchToggle}`}
        aria-label="Search"
        onClick={() => {
          setUnfolded(true);
          // Wait for the field to be displayed before moving focus to it.
          requestAnimationFrame(() => input.current?.focus());
        }}
      >
        <Icon name="search" />
      </button>
      <form
        ref={form}
        className={`${styles.search} ${unfolded ? styles.unfolded : ""}`}
        role="search"
        onSubmit={submit}
        onFocus={() => setFocused(true)}
        onBlur={(event) => {
          if (form.current?.contains(event.relatedTarget)) return;
          setFocused(false);
          setUnfolded(false);
        }}
        onKeyDown={(event) => {
          if (event.key === "Escape") input.current?.blur();
        }}
      >
        <span className={styles.searchIcon}>
          <Icon name="search" />
        </span>
        <input
          ref={input}
          className={styles.searchInput}
          type="search"
          role="combobox"
          autoComplete="off"
          spellCheck={false}
          maxLength={256}
          placeholder="Search"
          aria-label="Search"
          aria-keyshortcuts="Alt+S"
          aria-expanded={showResults}
          aria-controls="global-search-results"
          aria-haspopup="dialog"
          value={term}
          onChange={(event) => setTerm(event.target.value)}
        />
        <span className={styles.searchTrailing}>
          {!focused && <span aria-hidden="true">[Alt+S]</span>}
          <button
            type="button"
            className={styles.askAssistant}
            aria-label="Ask Amazon Q"
            onClick={onAskAssistant}
          >
            <AssistantGlyph />
            {focused && <strong>Ask Amazon Q</strong>}
          </button>
        </span>
        {showResults && (
          <div
            id="global-search-results"
            className={styles.searchResults}
            role="dialog"
            aria-label="Search results"
          >
            <h2>Hosted zones</h2>
            {results.data?.items.length ? (
              <ul>
                {results.data.items.map((zone) => (
                  <li key={zone.id}>
                    <button type="button" onClick={() => leave(routes.hostedZone(zone.id))}>
                      <strong>{displayName(zone.name)}</strong>
                      <span>
                        {zone.id}
                        {zone.description ? ` · ${zone.description}` : ""}
                      </span>
                    </button>
                  </li>
                ))}
              </ul>
            ) : (
              <p>{results.isPending ? "Searching…" : `No hosted zones match "${query}".`}</p>
            )}
            {results.data && results.data.total > results.data.items.length && (
              <p>Press Enter to see all {results.data.total} matches.</p>
            )}
          </div>
        )}
      </form>
    </>
  );
}

/** The dark bar across the top of every console page. */
export function GlobalHeader({ onShowShortcuts }: { onShowShortcuts: () => void }) {
  const router = useRouter();
  const notify = useNotify();
  const askAssistant = () => notify.info("Amazon Q is not available in this clone", ASSISTANT_NOTE);

  return (
    <header id="h" className={styles.header}>
      <nav className={styles.bar} aria-label="Global">
        <a
          className={styles.skip}
          href="#main-content"
          onClick={(event) => {
            event.preventDefault();
            const main = document.querySelector("main");
            main?.setAttribute("tabindex", "-1");
            main?.focus();
          }}
        >
          Skip to Main Content
        </a>
        <a
          className={styles.logo}
          href={routes.dashboard}
          title="Console Home"
          aria-label="Console Home"
          onClick={(event) => {
            event.preventDefault();
            router.push(routes.dashboard);
          }}
        >
          <Logo />
        </a>
        <span className={styles.divider} />
        <button
          type="button"
          className={`${styles.iconButton} ${styles.assistant}`}
          aria-label="Amazon Q"
          title="Amazon Q"
          onClick={askAssistant}
        >
          <AssistantTile />
        </button>
        <span className={styles.divider} />
        <ServicesMenu />
        <Search onAskAssistant={askAssistant} />
        <span className={styles.spacer} />
        <button
          type="button"
          className={styles.iconButton}
          aria-label="CloudShell"
          title="CloudShell"
          onClick={() =>
            notify.info(
              "CloudShell is not available in this clone",
              "This clone has no shell. Its REST API is documented at /api/docs.",
            )
          }
        >
          <Icon name="command-prompt" />
        </button>
        <span className={styles.divider} />
        <NotificationsMenu />
        <span className={styles.divider} />
        <HelpMenu onShowShortcuts={onShowShortcuts} />
        <AccountMenu />
      </nav>
    </header>
  );
}
