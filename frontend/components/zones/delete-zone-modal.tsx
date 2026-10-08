"use client";

import Alert from "@cloudscape-design/components/alert";
import Box from "@cloudscape-design/components/box";
import Button from "@cloudscape-design/components/button";
import FormField from "@cloudscape-design/components/form-field";
import Input from "@cloudscape-design/components/input";
import Modal from "@cloudscape-design/components/modal";
import SpaceBetween from "@cloudscape-design/components/space-between";
import { useState } from "react";

import { useNotify } from "@/components/shell/notifications";
import { useFollow } from "@/hooks/use-follow";
import { useDeleteHostedZone } from "@/hooks/use-hosted-zones";
import type { HostedZoneSummary } from "@/lib/api/types";
import { displayName } from "@/lib/format";
import { routes } from "@/lib/routes";

const CONFIRMATION = "delete";
/** Every zone has an NS and an SOA record that are deleted with it. */
const DEFAULT_RECORD_COUNT = 2;

interface DeleteZoneModalProps {
  zone: HostedZoneSummary;
  /** Offer a link to the zone's records. Not needed when already on that page. */
  showDetailsLink?: boolean;
  onDismiss: () => void;
  onDeleted: () => void;
}

/** Confirmation dialog for deleting a hosted zone; the user types "delete" to confirm. */
export function DeleteZoneModal({
  zone,
  showDetailsLink = true,
  onDismiss,
  onDeleted,
}: DeleteZoneModalProps) {
  const notify = useNotify();
  const follow = useFollow();
  const deleteZone = useDeleteHostedZone();
  const [confirmation, setConfirmation] = useState("");

  const name = displayName(zone.name);
  const hasOtherRecords = zone.record_count > DEFAULT_RECORD_COUNT;
  const confirmed = confirmation.trim().toLowerCase() === CONFIRMATION;

  const submit = () => {
    if (!confirmed) return;
    deleteZone.mutate(zone.id, {
      onSuccess: () => {
        notify.success(`Hosted zone ${name} was successfully deleted.`);
        onDeleted();
      },
      // As in the console, a rejected delete closes the dialog and reports in a flash.
      onError: (error) => {
        notify.error(error);
        onDismiss();
      },
    });
  };

  return (
    <Modal
      visible
      onDismiss={onDismiss}
      header={`Delete hosted zone ${name}?`}
      closeAriaLabel="Close modal"
      footer={
        <Box float="right">
          <SpaceBetween direction="horizontal" size="xs">
            <Button variant="link" onClick={onDismiss}>
              Cancel
            </Button>
            <Button
              variant="primary"
              disabled={!confirmed}
              loading={deleteZone.isPending}
              onClick={submit}
            >
              Delete
            </Button>
          </SpaceBetween>
        </Box>
      }
    >
      <SpaceBetween size="l">
        <Box>
          Delete the hosted zone permanently? This action cannot be undone. Your domain might become
          unavailable on the internet.
        </Box>
        {hasOtherRecords && (
          <Alert type="warning" header={`Take these actions to delete hosted zone ${name}`}>
            <SpaceBetween size="s">
              <Box>
                Complete the following steps to successfully delete this hosted zone. If you
                don&apos;t complete the steps, the deletion might be blocked by Route 53 service
                validation.
              </Box>
              <ul>
                <li>
                  Delete all records in this hosted zone, except the default NS and SOA records.
                </li>
              </ul>
              {showDetailsLink && (
                <Button href={routes.hostedZone(zone.id)} onFollow={follow}>
                  Go to hosted zone details
                </Button>
              )}
            </SpaceBetween>
          </Alert>
        )}
        <form
          onSubmit={(event) => {
            event.preventDefault();
            submit();
          }}
        >
          <FormField
            label={
              <>
                To confirm that you want to delete the hosted zone, enter <i>{CONFIRMATION}</i> in
                the field.
              </>
            }
          >
            <Input
              value={confirmation}
              placeholder={CONFIRMATION}
              ariaLabel={`Type ${CONFIRMATION} to confirm`}
              onChange={({ detail }) => setConfirmation(detail.value)}
              autoFocus
            />
          </FormField>
        </form>
      </SpaceBetween>
    </Modal>
  );
}
