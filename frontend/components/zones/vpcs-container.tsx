"use client";

import Alert from "@cloudscape-design/components/alert";
import AttributeEditor from "@cloudscape-design/components/attribute-editor";
import Container from "@cloudscape-design/components/container";
import Header from "@cloudscape-design/components/header";
import Input from "@cloudscape-design/components/input";
import Link from "@cloudscape-design/components/link";
import Select from "@cloudscape-design/components/select";
import SpaceBetween from "@cloudscape-design/components/space-between";
import { useState } from "react";

import { InfoLink } from "@/components/shell/help-context";
import type { VpcAssociation } from "@/lib/api/types";
import { awsRegions } from "@/lib/aws-regions";

export const EMPTY_VPC: VpcAssociation = { region: "", vpc_id: "" };

/** Whether every row names a Region and a VPC, and there is at least one. */
export function vpcsComplete(vpcs: readonly VpcAssociation[]): boolean {
  return vpcs.length > 0 && vpcs.every((vpc) => vpc.region && vpc.vpc_id.trim());
}

export function toApiVpcs(vpcs: readonly VpcAssociation[]): VpcAssociation[] {
  return vpcs.map((vpc) => ({ ...vpc, vpc_id: vpc.vpc_id.trim() }));
}

interface VpcsContainerProps {
  vpcs: VpcAssociation[];
  onChange: (vpcs: VpcAssociation[]) => void;
  /** Show the "required" errors; set once the form has been submitted. */
  showErrors: boolean;
}

/** The "VPCs to associate with the hosted zone" section of a private hosted zone. */
export function VpcsContainer({ vpcs, onChange, showErrors }: VpcsContainerProps) {
  const [noteVisible, setNoteVisible] = useState(true);

  const setVpc = (index: number, change: Partial<VpcAssociation>) => {
    onChange(vpcs.map((vpc, position) => (position === index ? { ...vpc, ...change } : vpc)));
  };

  return (
    <Container
      header={
        <Header
          variant="h2"
          info={<InfoLink topic="private-zone-vpcs" />}
          description="To use this hosted zone to resolve DNS queries for one or more VPCs, choose the VPCs. To associate a VPC with a hosted zone when the VPC was created using a different AWS account, you must use a programmatic method, such as the AWS CLI."
        >
          VPCs to associate with the hosted zone
        </Header>
      }
    >
      <SpaceBetween size="m">
        {noteVisible && (
          <Alert type="info" dismissible onDismiss={() => setNoteVisible(false)}>
            For each VPC that you associate with a private hosted zone, you must set the Amazon VPC
            settings{" "}
            <Link external href="https://docs.aws.amazon.com/vpc/latest/userguide/vpc-dns.html">
              enableDnsHostnames and enableDnsSupport
            </Link>{" "}
            to true.
          </Alert>
        )}
        <AttributeEditor
          items={vpcs}
          addButtonText="Add VPC"
          removeButtonText="Remove VPC"
          empty={
            showErrors
              ? "A private hosted zone must be associated with at least one VPC."
              : "No VPCs associated with the hosted zone."
          }
          onAddButtonClick={() => onChange([...vpcs, EMPTY_VPC])}
          onRemoveButtonClick={({ detail }) =>
            onChange(vpcs.filter((_vpc, index) => index !== detail.itemIndex))
          }
          definition={[
            {
              label: "Region",
              info: <InfoLink topic="vpc-region" />,
              control: (vpc, index) => (
                <Select
                  placeholder="Choose region"
                  selectedOption={awsRegions.find((region) => region.value === vpc.region) ?? null}
                  options={awsRegions}
                  filteringType="auto"
                  onChange={({ detail }) =>
                    setVpc(index, { region: detail.selectedOption.value ?? "" })
                  }
                />
              ),
              errorText: (vpc) => (showErrors && !vpc.region ? "Choose a Region." : undefined),
            },
            {
              label: "VPC ID",
              info: <InfoLink topic="vpc-id" />,
              control: (vpc, index) => (
                <Input
                  type="search"
                  value={vpc.vpc_id}
                  placeholder="Choose VPC"
                  spellcheck={false}
                  onChange={({ detail }) => setVpc(index, { vpc_id: detail.value })}
                />
              ),
              errorText: (vpc) =>
                showErrors && !vpc.vpc_id.trim()
                  ? "Enter a VPC ID, for example vpc-0a1b2c3d4e5f67890."
                  : undefined,
            },
          ]}
        />
      </SpaceBetween>
    </Container>
  );
}
