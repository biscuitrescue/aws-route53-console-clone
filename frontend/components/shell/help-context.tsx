"use client";

import Link from "@cloudscape-design/components/link";
import { createContext, useContext } from "react";

import { helpTopics } from "@/lib/help";
import type { HelpTopicId } from "@/lib/help";

/** Opens the help panel on a topic. Provided by `ConsolePage`. */
export const HelpContext = createContext<(topic: HelpTopicId) => void>(() => {});

/** The small "Info" link next to headings and field labels. */
export function InfoLink({ topic }: { topic: HelpTopicId }) {
  const openHelp = useContext(HelpContext);
  return (
    <Link
      variant="info"
      ariaLabel={`More information about ${helpTopics[topic].title}`}
      onFollow={(event) => {
        event.preventDefault();
        openHelp(topic);
      }}
    >
      Info
    </Link>
  );
}
