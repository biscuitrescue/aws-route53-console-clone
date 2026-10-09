"use client";

import Box from "@cloudscape-design/components/box";
import ColumnLayout from "@cloudscape-design/components/column-layout";
import type { ReactNode } from "react";

import type { HostedZone } from "@/lib/api/types";
import { displayName, formatNumber, orDash, zoneTypeLongLabel } from "@/lib/format";

import styles from "./zone-details-list.module.css";

interface ZoneDetailItem {
  label: string;
  value: ReactNode;
}

function Detail({ label, value }: ZoneDetailItem) {
  return (
    <div>
      <Box variant="awsui-key-label">{label}</Box>
      <div>{value}</div>
    </div>
  );
}

/**
 * The facts the console lists about a hosted zone. The zone page lays them out in three
 * columns; the side panel of the zones list stacks the same columns and bullets the name
 * servers.
 */
export function ZoneDetailsList({
  zone,
  stacked = false,
}: {
  zone: HostedZone;
  stacked?: boolean;
}) {
  const identity: ZoneDetailItem[] = [
    { label: "Hosted zone name", value: displayName(zone.name) },
    { label: "Hosted zone ID", value: zone.id },
    { label: "Description", value: orDash(zone.description) },
  ];
  const queryLog: ZoneDetailItem = { label: "Query log", value: "-" };
  const facts: ZoneDetailItem[] = [
    { label: "Type", value: zoneTypeLongLabel[zone.type] },
    { label: "Record count", value: formatNumber(zone.record_count) },
  ];
  const servers: ZoneDetailItem[] = [
    ...(zone.type === "private"
      ? [
          {
            label: "Associated VPCs",
            value: (
              <ul className={styles.list}>
                {zone.vpcs.map((vpc) => (
                  <li key={vpc.vpc_id}>
                    {vpc.vpc_id} | {vpc.region}
                  </li>
                ))}
              </ul>
            ),
          },
        ]
      : []),
    {
      label: "Name servers",
      value: (
        <ul className={styles.list}>
          {zone.name_servers.map((server) => (
            <li key={server}>{displayName(server)}</li>
          ))}
        </ul>
      ),
    },
  ];

  const group = (items: ZoneDetailItem[]) => (
    <div className={styles.group}>
      {items.map((item) => (
        <Detail key={item.label} {...item} />
      ))}
    </div>
  );

  if (stacked) {
    return (
      <div className={styles.stacked}>
        <div className={styles.block}>
          {group(identity.slice(0, 2))}
          {group(identity.slice(2))}
          {group([queryLog])}
        </div>
        {group(facts)}
        {group(servers)}
      </div>
    );
  }
  return (
    <ColumnLayout columns={3} variant="text-grid">
      {group(identity)}
      {group([queryLog, ...facts])}
      {group(servers)}
    </ColumnLayout>
  );
}
