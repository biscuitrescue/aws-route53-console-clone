"use client";

import Link from "@cloudscape-design/components/link";

/** The line the console shows under both table headers. */
export function SearchModeNote({ onOpenSettings }: { onOpenSettings: () => void }) {
  return (
    <>
      Automatic mode is the current search behavior optimized for best filter results.{" "}
      <Link
        variant="primary"
        fontSize="inherit"
        href="#"
        onFollow={(event) => {
          event.preventDefault();
          onOpenSettings();
        }}
      >
        To change modes go to settings.
      </Link>
    </>
  );
}
