"use client";

import Box from "@cloudscape-design/components/box";
import type { ReactNode } from "react";

import type { HostedZone } from "@/lib/api/types";
import { displayName, formatNumber, orDash, zoneTypeLongLabel } from "@/lib/format";

export interface ZoneDetailItem {
  label: string;
  value: ReactNode;
}

/** The facts the console lists about a hosted zone, in its order. */
export function zoneDetailItems(zone: HostedZone): ZoneDetailItem[] {
  return [
    { label: "Hosted zone name", value: displayName(zone.name) },
    { label: "Hosted zone ID", value: zone.id },
    { label: "Description", value: orDash(zone.description) },
    { label: "Query log", value: "-" },
    { label: "Type", value: zoneTypeLongLabel[zone.type] },
    { label: "Record count", value: formatNumber(zone.record_count) },
    ...(zone.type === "private"
      ? [
          {
            label: "Associated VPCs",
            value: (
              <ul>
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
        <ul>
          {zone.name_servers.map((server) => (
            <li key={server}>{displayName(server)}</li>
          ))}
        </ul>
      ),
    },
  ];
}

/** Zone facts stacked vertically, for the side panel. */
export function ZoneDetailsList({ zone }: { zone: HostedZone }) {
  return (
    <div>
      {zoneDetailItems(zone).map((item) => (
        <Box key={item.label} margin={{ bottom: "l" }}>
          <Box variant="awsui-key-label">{item.label}</Box>
          <div>{item.value}</div>
        </Box>
      ))}
    </div>
  );
}
