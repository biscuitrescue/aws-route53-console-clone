"use client";

import AppLayoutToolbar from "@cloudscape-design/components/app-layout-toolbar";
import type { AppLayoutProps } from "@cloudscape-design/components/app-layout";
import BreadcrumbGroup from "@cloudscape-design/components/breadcrumb-group";
import Flashbar from "@cloudscape-design/components/flashbar";
import HelpPanel from "@cloudscape-design/components/help-panel";
import Icon from "@cloudscape-design/components/icon";
import SideNavigation from "@cloudscape-design/components/side-navigation";
import { usePathname } from "next/navigation";
import { useCallback, useEffect, useState } from "react";
import type { ReactNode } from "react";

import { useFollow } from "@/hooks/use-follow";
import { usePersistedState } from "@/hooks/use-persisted-state";
import { useSession } from "@/hooks/use-session";
import { helpTopics } from "@/lib/help";
import type { HelpTopicId } from "@/lib/help";
import { navigationItems, placeholderSections, placeholderHref } from "@/lib/navigation";
import { routes } from "@/lib/routes";

import { HelpContext } from "./help-context";
import { useNotificationItems } from "./notifications";

export interface Breadcrumb {
  text: string;
  href: string;
}

interface ConsolePageProps {
  /** First part of the browser tab title; the account name is appended. */
  title: string;
  /** Trail after "Route 53". The last entry is the current page. */
  breadcrumbs: Breadcrumb[];
  /** Topic shown when the help panel is opened from the toolbar. */
  helpTopic: HelpTopicId;
  /** List pages open with the navigation showing; form pages hide it, as in the console. */
  navigationOpen?: boolean;
  contentType?: AppLayoutProps.ContentType;
  /** A Cloudscape `SplitPanel`, for pages that show details of the selected row. */
  splitPanel?: ReactNode;
  /** Control the split panel from the page; by default it starts open and the user toggles it. */
  splitPanelOpen?: boolean;
  onSplitPanelToggle?: (open: boolean) => void;
  children: ReactNode;
}

const DEFAULT_SPLIT_PANEL: AppLayoutProps.SplitPanelPreferences = { position: "side" };
const SPLIT_PANEL_SIZE = 400;
const NAVIGATION_WIDTH = 280;

/** The navigation highlights the section a page belongs to, not only exact matches. */
function activeNavigationHref(pathname: string): string {
  if (pathname.startsWith(routes.hostedZones)) return routes.hostedZones;
  const section = placeholderSections.find((candidate) =>
    pathname.startsWith(placeholderHref(candidate)),
  );
  return section ? placeholderHref(section) : pathname;
}

/**
 * The console layout around one page: toolbar with breadcrumbs, side navigation,
 * notifications, help panel and an optional split panel.
 */
export function ConsolePage({
  title,
  breadcrumbs,
  helpTopic,
  navigationOpen: navigationOpenByDefault = true,
  contentType = "default",
  splitPanel,
  splitPanelOpen: controlledSplitPanelOpen,
  onSplitPanelToggle,
  children,
}: ConsolePageProps) {
  const pathname = usePathname();
  const follow = useFollow();
  const notifications = useNotificationItems();
  const { data: session } = useSession();

  const [navigationOpen, setNavigationOpen] = useState(navigationOpenByDefault);
  const [toolsOpen, setToolsOpen] = useState(false);
  const [topic, setTopic] = useState<HelpTopicId>(helpTopic);
  const [ownSplitPanelOpen, setOwnSplitPanelOpen] = useState(true);
  const splitPanelOpen = controlledSplitPanelOpen ?? ownSplitPanelOpen;
  const [splitPanelPreferences, setSplitPanelPreferences] = usePersistedState(
    "splitPanel.preferences",
    DEFAULT_SPLIT_PANEL,
  );
  const [splitPanelSize, setSplitPanelSize] = usePersistedState(
    "splitPanel.size",
    SPLIT_PANEL_SIZE,
  );

  const account = session?.user.display_name;
  useEffect(() => {
    document.title = account ? `${title} | ${account}` : title;
  }, [title, account]);

  const openHelp = useCallback((next: HelpTopicId) => {
    setTopic(next);
    setToolsOpen(true);
  }, []);

  const help = helpTopics[topic];
  const learnMore = "learnMore" in help ? help.learnMore : undefined;

  return (
    <HelpContext.Provider value={openHelp}>
      <AppLayoutToolbar
        headerSelector="#h"
        footerSelector="#f"
        contentType={contentType}
        navigationWidth={NAVIGATION_WIDTH}
        navigationOpen={navigationOpen}
        onNavigationChange={({ detail }) => setNavigationOpen(detail.open)}
        navigation={
          <SideNavigation
            header={{ text: "Route 53", href: routes.hostedZones }}
            items={navigationItems}
            activeHref={activeNavigationHref(pathname)}
            onFollow={follow}
          />
        }
        breadcrumbs={
          <BreadcrumbGroup
            items={[{ text: "Route 53", href: routes.dashboard }, ...breadcrumbs]}
            ariaLabel="Breadcrumbs"
            onFollow={follow}
          />
        }
        notifications={<Flashbar items={notifications} stackItems />}
        toolsOpen={toolsOpen}
        onToolsChange={({ detail }) => {
          setToolsOpen(detail.open);
          if (!detail.open) setTopic(helpTopic);
        }}
        tools={
          <HelpPanel
            header={<h2>{help.title}</h2>}
            footer={
              learnMore && (
                <>
                  <h3>
                    Learn more <Icon name="external" />
                  </h3>
                  <ul>
                    {learnMore.map((link) => (
                      <li key={link.href}>
                        <a href={link.href} target="_blank" rel="noopener noreferrer">
                          {link.text}
                        </a>
                      </li>
                    ))}
                  </ul>
                </>
              )
            }
          >
            {help.body}
          </HelpPanel>
        }
        splitPanel={splitPanel}
        splitPanelOpen={splitPanelOpen}
        onSplitPanelToggle={({ detail }) => {
          setOwnSplitPanelOpen(detail.open);
          onSplitPanelToggle?.(detail.open);
        }}
        splitPanelPreferences={splitPanelPreferences}
        onSplitPanelPreferencesChange={({ detail }) => setSplitPanelPreferences(detail)}
        splitPanelSize={splitPanelSize}
        onSplitPanelResize={({ detail }) => setSplitPanelSize(detail.size)}
        content={children}
      />
    </HelpContext.Provider>
  );
}
