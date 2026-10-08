"use client";

import Icon from "@cloudscape-design/components/icon";
import type { IconProps } from "@cloudscape-design/components/icon";
import { useRouter } from "next/navigation";
import { useEffect, useRef, useState } from "react";
import type { FormEvent } from "react";

import { useSession, useSignOut } from "@/hooks/use-session";
import { useVisualMode } from "@/hooks/use-visual-mode";
import type { VisualMode } from "@/hooks/use-visual-mode";
import { routes } from "@/lib/routes";

import styles from "./global-header.module.css";
import { Logo } from "./logo";

const VISUAL_MODES: { mode: VisualMode; label: string; icon: IconProps.Name }[] = [
  { mode: "auto", label: "Browser default", icon: "multiscreen" },
  { mode: "light", label: "Light", icon: "light-dark" },
  { mode: "dark", label: "Dark", icon: "star" },
];

/** Account IDs are shown in groups of four, as AWS prints them. */
function formatAccountId(accountId: string): string {
  return accountId.replace(/(\d{4})(?=\d)/g, "$1-");
}

function AccountMenu() {
  const router = useRouter();
  const { data: session } = useSession();
  const signOut = useSignOut();
  const [visualMode, setVisualMode] = useVisualMode();
  const [open, setOpen] = useState(false);
  const container = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (!open) return;
    const close = (event: MouseEvent | KeyboardEvent) => {
      const outside =
        event instanceof MouseEvent && !container.current?.contains(event.target as Node);
      const escape = event instanceof KeyboardEvent && event.key === "Escape";
      if (outside || escape) setOpen(false);
    };
    document.addEventListener("mousedown", close);
    document.addEventListener("keydown", close);
    return () => {
      document.removeEventListener("mousedown", close);
      document.removeEventListener("keydown", close);
    };
  }, [open]);

  const user = session?.user;
  const handleSignOut = () => {
    signOut.mutate(undefined, { onSettled: () => router.replace(routes.signIn) });
  };

  return (
    <div className={styles.account} ref={container}>
      <button
        type="button"
        className={styles.accountButton}
        aria-haspopup="menu"
        aria-expanded={open}
        aria-label={user ? `Account menu for ${user.display_name}` : "Account menu"}
        onClick={() => setOpen((current) => !current)}
      >
        <span className={styles.accountName}>
          {user?.display_name ?? "Account"}
          <Icon name={open ? "caret-up-filled" : "caret-down-filled"} size="small" />
        </span>
        <span>{user?.email}</span>
      </button>
      {open && (
        <div className={styles.menu} role="menu" aria-label="Account">
          <div className={styles.menuHeader}>
            <div className={styles.menuTitle}>{user?.display_name}</div>
            <div className={styles.menuMeta}>
              Account ID: {user ? formatAccountId(user.account_id) : ""}
            </div>
            <div className={styles.menuMeta}>Signed in as {user?.email}</div>
          </div>
          <div className={styles.menuSeparator} />
          <div className={styles.menuRow}>
            <span id="visual-mode-label">Visual mode</span>
            <div className={styles.modes} role="group" aria-labelledby="visual-mode-label">
              {VISUAL_MODES.map(({ mode, label, icon }) => (
                <button
                  key={mode}
                  type="button"
                  className={styles.modeButton}
                  aria-label={label}
                  aria-pressed={visualMode === mode}
                  title={label}
                  onClick={() => setVisualMode(mode)}
                >
                  <Icon name={icon} />
                </button>
              ))}
            </div>
          </div>
          <div className={styles.menuSeparator} />
          <button type="button" role="menuitem" className={styles.menuItem} onClick={handleSignOut}>
            Sign out of {user?.display_name}
            <Icon name="sign-out" />
          </button>
        </div>
      )}
    </div>
  );
}

function Search() {
  const router = useRouter();
  const input = useRef<HTMLInputElement>(null);
  const [term, setTerm] = useState("");

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

  const submit = (event: FormEvent) => {
    event.preventDefault();
    const query = term.trim();
    router.push(
      query ? `${routes.hostedZones}?search=${encodeURIComponent(query)}` : routes.hostedZones,
    );
    setTerm("");
    input.current?.blur();
  };

  return (
    <form className={styles.search} role="search" onSubmit={submit}>
      <span className={styles.searchIcon}>
        <Icon name="search" />
      </span>
      <input
        ref={input}
        className={styles.searchInput}
        type="search"
        placeholder="Search"
        aria-label="Search hosted zones"
        aria-keyshortcuts="Alt+S"
        value={term}
        onChange={(event) => setTerm(event.target.value)}
      />
      <span className={styles.searchHint} aria-hidden="true">
        [Alt+S]
      </span>
    </form>
  );
}

/** The dark bar across the top of every console page. */
export function GlobalHeader() {
  const router = useRouter();
  return (
    <header id="h" className={styles.header}>
      <a
        className={styles.logo}
        href={routes.hostedZones}
        aria-label="Route 53 console home"
        onClick={(event) => {
          event.preventDefault();
          router.push(routes.hostedZones);
        }}
      >
        <Logo />
      </a>
      <span className={styles.divider} />
      <button
        type="button"
        className={styles.iconButton}
        aria-label="Assistant (not available in this clone)"
      >
        <span className={styles.assistant}>
          <Icon name="gen-ai" size="small" />
        </span>
      </button>
      <span className={styles.divider} />
      <button type="button" className={styles.iconButton} aria-label="Services">
        <Icon name="grid-view" />
      </button>
      <Search />
      <span className={styles.spacer} />
      <button
        type="button"
        className={styles.iconButton}
        aria-label="CloudShell (not available in this clone)"
      >
        <Icon name="command-prompt" />
      </button>
      <span className={styles.divider} />
      <button
        type="button"
        className={styles.iconButton}
        aria-label="Notifications (none available)"
      >
        <Icon name="notification" />
      </button>
      <span className={styles.divider} />
      <a
        className={styles.iconButton}
        href="https://docs.aws.amazon.com/Route53/latest/DeveloperGuide/Welcome.html"
        target="_blank"
        rel="noopener noreferrer"
        aria-label="Help: Route 53 documentation (opens in a new tab)"
      >
        <Icon name="support" />
      </a>
      <AccountMenu />
    </header>
  );
}
