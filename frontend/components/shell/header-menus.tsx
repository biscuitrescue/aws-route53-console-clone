"use client";

import Icon from "@cloudscape-design/components/icon";
import { useRouter } from "next/navigation";
import { useCallback, useEffect, useRef, useState } from "react";
import type { ReactNode, RefObject } from "react";

import { useSession, useSignOut } from "@/hooks/use-session";
import { useVisualMode } from "@/hooks/use-visual-mode";
import type { VisualMode } from "@/hooks/use-visual-mode";
import { routes } from "@/lib/routes";

import styles from "./global-header.module.css";
import { MonitorGlyph, MoonGlyph, ServicesGlyph, SignOutGlyph, SunGlyph } from "./header-icons";
import { useNotify } from "./notifications";

/** Close a menu on Escape or on a press outside `container`. */
function useDismiss(open: boolean, close: () => void): RefObject<HTMLDivElement | null> {
  const container = useRef<HTMLDivElement>(null);
  useEffect(() => {
    if (!open) return;
    const onPointerDown = (event: MouseEvent) => {
      if (!container.current?.contains(event.target as Node)) close();
    };
    const onKeyDown = (event: KeyboardEvent) => {
      if (event.key === "Escape") close();
    };
    document.addEventListener("mousedown", onPointerDown);
    document.addEventListener("keydown", onKeyDown);
    return () => {
      document.removeEventListener("mousedown", onPointerDown);
      document.removeEventListener("keydown", onKeyDown);
    };
  }, [open, close]);
  return container;
}

function useMenu() {
  const [open, setOpen] = useState(false);
  const close = useCallback(() => setOpen(false), []);
  const container = useDismiss(open, close);
  return { open, close, toggle: () => setOpen((current) => !current), container };
}

/** Says plainly that a console feature exists only as a label in this clone. */
function useNotAvailable() {
  const notify = useNotify();
  return (feature: string) =>
    notify.info(
      `${feature} is not available in this clone`,
      "This clone implements Route 53 hosted zones and records. Other AWS services, account settings and billing are mocked.",
    );
}

const SERVICE_VIEWS = ["Recently visited", "Favorites", "All applications", "All services"];

const SERVICE_CATEGORIES = [
  "Analytics",
  "Application Integration",
  "Business Applications",
  "Cloud Financial Management",
  "Compute",
  "Containers",
  "Customer Enablement",
  "Database",
  "Developer Tools",
  "Front-end Web & Mobile",
  "Internet of Things",
  "Machine Learning",
  "Management & Governance",
  "Migration & Transfer",
  "Networking & Content Delivery",
  "Security, Identity, & Compliance",
  "Storage",
];

/** Views of the services menu that list Route 53: it is the only service in the clone. */
const VIEWS_WITH_ROUTE_53 = new Set([
  "Recently visited",
  "All services",
  "Networking & Content Delivery",
]);

export function ServicesMenu() {
  const router = useRouter();
  const { open, close, toggle, container } = useMenu();
  const [view, setView] = useState(SERVICE_VIEWS[0]);

  const go = (href: string) => {
    close();
    router.push(href);
  };

  const viewButton = (name: string) => (
    <li key={name}>
      <button
        type="button"
        className={styles.servicesView}
        aria-current={view === name ? "page" : undefined}
        onClick={() => setView(name)}
      >
        {name}
      </button>
    </li>
  );

  return (
    <div className={styles.menuAnchor} ref={container}>
      <button
        type="button"
        className={`${styles.iconButton} ${styles.wide}`}
        aria-label="Services"
        aria-expanded={open}
        title="Services"
        onClick={toggle}
      >
        <ServicesGlyph />
      </button>
      {open && (
        <div className={styles.services} role="dialog" aria-label="Services">
          <nav className={styles.servicesViews} aria-label="Service categories">
            <ul>{SERVICE_VIEWS.map(viewButton)}</ul>
            <hr />
            <ul>{SERVICE_CATEGORIES.map(viewButton)}</ul>
          </nav>
          <div className={styles.servicesPane}>
            <div className={styles.servicesPaneHeader}>
              <h2>{view}</h2>
              <button
                type="button"
                className={styles.plainButton}
                aria-label="Close"
                onClick={close}
              >
                <Icon name="close" size="medium" />
              </button>
            </div>
            {VIEWS_WITH_ROUTE_53.has(view) ? (
              <ul className={styles.servicesList}>
                <li>
                  <button type="button" onClick={() => go(routes.dashboard)}>
                    <strong>Route 53</strong>
                    <span>Scalable DNS and Domain Name Registration</span>
                  </button>
                </li>
                {view === "Recently visited" && (
                  <li>
                    <button type="button" onClick={() => go(routes.hostedZones)}>
                      <strong>Console Home</strong>
                      <span>View resource insights, service shortcuts, and feature updates</span>
                    </button>
                  </li>
                )}
              </ul>
            ) : (
              <p className={styles.servicesEmpty}>
                Nothing to show here. Route 53 is the only service in this clone; find it under
                Networking &amp; Content Delivery.
              </p>
            )}
          </div>
        </div>
      )}
    </div>
  );
}

export function NotificationsMenu() {
  const { open, close, toggle, container } = useMenu();
  const notAvailable = useNotAvailable();
  return (
    <div className={styles.menuAnchor} ref={container}>
      <button
        type="button"
        className={`${styles.iconButton} ${styles.wide}`}
        aria-label="Notifications (none available)"
        aria-haspopup="menu"
        aria-expanded={open}
        title="Notifications"
        onClick={toggle}
      >
        <Icon name="notification" />
      </button>
      {open && (
        <div
          className={`${styles.menu} ${styles.notifications}`}
          role="dialog"
          aria-label="Notifications"
        >
          <div className={styles.notificationsHeader}>
            <h3>Notifications</h3>
            <button
              type="button"
              onClick={() => {
                close();
                notAvailable("Notification center");
              }}
            >
              Notification center
            </button>
          </div>
          <div className={styles.notificationsEmpty}>
            <strong>No notifications</strong>
            <p>AWS managed notifications are automatically generated by AWS.</p>
          </div>
        </div>
      )}
    </div>
  );
}

const SUPPORT_LINKS = [
  [
    { text: "Support Center", href: "https://console.aws.amazon.com/support/home" },
    { text: "re:Post", href: "https://repost.aws/tags?search=Route 53" },
  ],
  [
    { text: "Documentation", href: "https://docs.aws.amazon.com/route53/" },
    { text: "Training", href: "https://aws.amazon.com/training/" },
    { text: "Getting Started Resource Center", href: "https://aws.amazon.com/resources/" },
  ],
];

export function HelpMenu({ onShowShortcuts }: { onShowShortcuts: () => void }) {
  const { open, close, toggle, container } = useMenu();
  const notAvailable = useNotAvailable();
  return (
    <div className={styles.menuAnchor} ref={container}>
      <button
        type="button"
        className={`${styles.iconButton} ${styles.wide}`}
        aria-label="Help & support"
        aria-expanded={open}
        onClick={toggle}
      >
        <Icon name="support" />
      </button>
      {open && (
        <div className={`${styles.menu} ${styles.support}`}>
          <h3 className={styles.menuHeading}>
            <a
              href="https://aws.amazon.com/premiumsupport/"
              target="_blank"
              rel="noopener noreferrer"
            >
              Support <Icon name="external" ariaLabel="Opens in a new tab" />
            </a>
          </h3>
          <hr className={styles.fullRule} />
          {SUPPORT_LINKS.map((group) => (
            <div key={group[0].text}>
              <ul role="menu">
                {group.map((link) => (
                  <li key={link.text} role="menuitem">
                    <a href={link.href} target="_blank" rel="noopener noreferrer" onClick={close}>
                      {link.text}
                    </a>
                  </li>
                ))}
              </ul>
              <hr />
            </div>
          ))}
          {/* The clone's own help: not in the console, so it sits apart from the AWS links. */}
          <ul role="menu">
            <li role="menuitem">
              <button
                type="button"
                onClick={() => {
                  close();
                  onShowShortcuts();
                }}
              >
                Keyboard shortcuts
              </button>
            </li>
            <li role="menuitem">
              <a href="/api/docs" target="_blank" rel="noopener noreferrer" onClick={close}>
                API reference
              </a>
            </li>
          </ul>
          <hr />
          <button
            type="button"
            className={styles.feedback}
            onClick={() => {
              close();
              notAvailable("Feedback");
            }}
          >
            Send feedback
          </button>
        </div>
      )}
    </div>
  );
}

const VISUAL_MODES: { mode: VisualMode; label: string; icon: ReactNode }[] = [
  { mode: "auto", label: "Browser default", icon: <MonitorGlyph /> },
  { mode: "light", label: "Light", icon: <SunGlyph /> },
  { mode: "dark", label: "Dark", icon: <MoonGlyph /> },
];

/** The console's account pages, which the clone mocks. */
const ACCOUNT_PAGES = ["Projects", "Team", "Billing", "Profile"];

/** Account IDs are shown in groups of four, as AWS prints them. */
function formatAccountId(accountId: string): string {
  return accountId.replace(/(\d{4})(?=\d)/g, "$1-");
}

export function AccountMenu() {
  const router = useRouter();
  const { data: session } = useSession();
  const signOut = useSignOut();
  const [visualMode, setVisualMode] = useVisualMode();
  const { open, close, toggle, container } = useMenu();
  const notAvailable = useNotAvailable();

  const user = session?.user;
  const account = user?.display_name ?? "Account";

  const handleSignOut = () => {
    signOut.mutate(undefined, { onSettled: () => router.replace(routes.signIn) });
  };

  const mocked = (feature: string, trailing: ReactNode = <Icon name="external" />) => (
    <button
      key={feature}
      type="button"
      role="menuitem"
      className={styles.menuItem}
      onClick={() => {
        close();
        notAvailable(feature);
      }}
    >
      {feature}
      {trailing}
    </button>
  );

  return (
    <div className={styles.menuAnchor} ref={container}>
      <button
        type="button"
        className={styles.accountButton}
        aria-haspopup="menu"
        aria-expanded={open}
        aria-label={`Account menu for ${account}`}
        title={user?.email}
        onClick={toggle}
      >
        <span className={styles.accountName}>
          {account}
          <span className={styles.caret} aria-hidden="true" />
        </span>
        <span>{user?.email}</span>
      </button>
      {open && (
        <div className={`${styles.menu} ${styles.accountMenu}`} role="menu" aria-label="Account">
          {mocked(account)}
          <div className={styles.accountSummary}>
            <span>Account</span>
            <div>
              <div>
                <span>Account ID</span>
                <span>{user ? formatAccountId(user.account_id) : ""}</span>
              </div>
              <div>
                <span>Signed in as</span>
                <span>{user?.email}</span>
              </div>
            </div>
          </div>
          {mocked("Switch project")}
          <hr />
          {ACCOUNT_PAGES.map((page) => mocked(page))}
          <hr />
          {mocked("Language", <Icon name="angle-right" />)}
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
                  {icon}
                </button>
              ))}
            </div>
          </div>
          <hr />
          <button type="button" role="menuitem" className={styles.menuItem} onClick={handleSignOut}>
            Sign out of {account}
            <SignOutGlyph />
          </button>
        </div>
      )}
    </div>
  );
}
