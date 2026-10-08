"use client";

import Box from "@cloudscape-design/components/box";
import Button from "@cloudscape-design/components/button";
import Modal from "@cloudscape-design/components/modal";
import Table from "@cloudscape-design/components/table";

import { useRegisteredShortcuts } from "@/hooks/use-shortcuts";
import type { Shortcut } from "@/hooks/use-shortcuts";

const ALWAYS_AVAILABLE: Shortcut[] = [
  { key: "Alt + S", description: "Focus the search field in the top bar" },
  { key: "?", description: "Show this list of keyboard shortcuts" },
];

export function ShortcutsModal({ onDismiss }: { onDismiss: () => void }) {
  const pageShortcuts = useRegisteredShortcuts();
  return (
    <Modal
      visible
      onDismiss={onDismiss}
      header="Keyboard shortcuts"
      footer={
        <Box float="right">
          <Button variant="primary" onClick={onDismiss}>
            Close
          </Button>
        </Box>
      }
    >
      <Table
        variant="embedded"
        items={[...pageShortcuts, ...ALWAYS_AVAILABLE]}
        trackBy="key"
        columnDefinitions={[
          {
            id: "key",
            header: "Key",
            width: 140,
            cell: (item) => <Box variant="code">{item.key}</Box>,
          },
          { id: "description", header: "Action", cell: (item) => item.description },
        ]}
      />
    </Modal>
  );
}
