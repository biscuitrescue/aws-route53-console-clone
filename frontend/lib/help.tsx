import type { ReactNode } from "react";

interface HelpLink {
  text: string;
  href: string;
}

export interface HelpTopic {
  title: string;
  body: ReactNode;
  learnMore?: HelpLink[];
}

const DOCS = "https://docs.aws.amazon.com/Route53/latest/DeveloperGuide";

/** Content of the help panel, keyed by the id an Info link passes. Wording follows the console. */
export const helpTopics = {
  "hosted-zones": {
    title: "Hosted zones",
    body: (
      <>
        <p>
          A hosted zone is a container for records, and records contain information about how you
          want to route traffic for a specific domain, such as example.com, and its subdomains. A
          hosted zone and the corresponding domain have the same name.
        </p>
        <p>
          <b>Public hosted zones</b> contain records that specify how you want to route traffic on
          the internet. <b>Private hosted zones</b> contain records that specify how you want to
          route traffic in an Amazon VPC.
        </p>
      </>
    ),
    learnMore: [
      { text: "Working with hosted zones", href: `${DOCS}/hosted-zones-working-with.html` },
    ],
  },
  "create-hosted-zone": {
    title: "Create hosted zone",
    body: (
      <>
        <p>
          You create a hosted zone when you want to use Route 53 to route internet traffic for your
          domain or to route traffic within your VPCs. Then you create records in the hosted zone
          for the domain name (example.com) and subdomains (such as www.example.com or
          blog.example.com).
        </p>
        <p>
          When you register a domain with Route 53, a public hosted zone is automatically created.
          You can also create a new hosted zone for a subdomain. Using a separate hosted zone to
          route internet traffic for a subdomain is sometimes known as &quot;delegating
          responsibility for a subdomain to a hosted zone&quot; or &quot;delegating a subdomain to
          other name servers&quot;.
        </p>
        <p>
          When you want to route traffic to your VPCs you create a private hosted zone for your
          domain and associate a VPC to it. This is sometimes referred to as &quot;private
          DNS&quot;.
        </p>
      </>
    ),
    learnMore: [
      { text: "Working with public hosted zones", href: `${DOCS}/AboutHZWorkingWith.html` },
      { text: "Working with private hosted zones", href: `${DOCS}/hosted-zones-private.html` },
      {
        text: "How internet traffic is routed to your website or web application",
        href: `${DOCS}/welcome-dns-service.html`,
      },
    ],
  },
  "domain-name": {
    title: "Domain name",
    body: (
      <p>
        The name of the domain that you want to route traffic for, for example example.com. Route 53
        treats the name as fully qualified whether or not you include a trailing dot.
      </p>
    ),
    learnMore: [{ text: "DNS domain name format", href: `${DOCS}/DomainNameFormat.html` }],
  },
  description: {
    title: "Description",
    body: (
      <p>
        In the list of hosted zones, this value lets you distinguish hosted zones that have the same
        name. A description is optional and can be up to 256 characters.
      </p>
    ),
  },
  "zone-type": {
    title: "Type",
    body: (
      <p>
        The type specifies whether this is a public hosted zone (for routing traffic on the
        internet) or a private hosted zone (for routing traffic within and among VPCs). You
        can&apos;t change the type after the hosted zone is created.
      </p>
    ),
  },
  "private-zone-vpcs": {
    title: "VPCs to associate with the hosted zone",
    body: (
      <>
        <p>
          A private hosted zone answers DNS queries only from the VPCs that you associate with it.
          You must associate at least one VPC when you create the hosted zone.
        </p>
        <p>
          This clone does not look VPCs up: enter the ID of any VPC, for example
          vpc-0a1b2c3d4e5f67890.
        </p>
      </>
    ),
    learnMore: [
      { text: "Working with private hosted zones", href: `${DOCS}/hosted-zones-private.html` },
    ],
  },
  "vpc-region": {
    title: "Region",
    body: <p>The AWS Region that the VPC was created in.</p>,
  },
  "vpc-id": {
    title: "VPC ID",
    body: (
      <p>
        The ID of the VPC that you want to associate with the hosted zone. A VPC ID is{" "}
        <code>vpc-</code> followed by 8 or 17 hexadecimal characters.
      </p>
    ),
  },
  tags: {
    title: "Tags",
    body: (
      <p>
        A tag is a label that you assign to an AWS resource. Each tag consists of a key and an
        optional value. You can use tags to organize your hosted zones and to track costs.
      </p>
    ),
    learnMore: [
      { text: "Tagging Amazon Route 53 resources", href: `${DOCS}/tagging-resources.html` },
    ],
  },
  "zone-details": {
    title: "Hosted zone details",
    body: (
      <>
        <p>The details page for a hosted zone include the following information:</p>
        <p>
          <b>Hosted zone ID:</b> Route 53 assigns the ID when you create a hosted zone. The main use
          for this ID is programmatic access to the hosted zone.
        </p>
        <p>
          <b>Description:</b> In the list of hosted zones, this value lets you distinguish hosted
          zones that have the same name. A description is optional.
        </p>
        <p>
          <b>Type:</b> The type specifies whether this is a public hosted zone (for routing traffic
          on the internet) or a private hosted zone (for routing traffic within and among VPCs).
        </p>
        <p>
          <b>Name servers:</b> Route 53 assigns name servers when you create a hosted zone. The
          assigned name servers can&apos;t be changed.
        </p>
        <p>
          To make Route 53 the DNS service for a domain (to use the records in a public hosted zone
          to route traffic on the internet for a domain), you update the domain registration to use
          these name servers.
        </p>
        <p>
          <b>Record count:</b> The total number of records in a hosted zone, including the default
          NS and SOA records.
        </p>
      </>
    ),
    learnMore: [
      {
        text: "Making Route 53 the DNS service for an existing domain",
        href: `${DOCS}/MigratingDNS.html`,
      },
    ],
  },
  records: {
    title: "Records",
    body: (
      <>
        <p>
          After you create a hosted zone for your domain, you create records to tell the Domain Name
          System (DNS) how you want traffic to be routed for that domain.
        </p>
        <p>
          The name of each record in a hosted zone must end with the name of the hosted zone. Route
          53 creates the NS and SOA records for the zone itself; they can be edited but not deleted.
        </p>
      </>
    ),
    learnMore: [{ text: "Working with records", href: `${DOCS}/rrsets-working-with.html` }],
  },
  "create-record": {
    title: "Create record",
    body: (
      <p>
        Quick create lets you define one or more records on a single page. Every record needs a
        name, a type and either one or more values or an alias target.
      </p>
    ),
    learnMore: [
      {
        text: "Creating records by using the console",
        href: `${DOCS}/resource-record-sets-creating.html`,
      },
    ],
  },
  "record-name": {
    title: "Record name",
    body: (
      <p>
        To route traffic to a subdomain, enter the subdomain name. For example, to route traffic to
        blog.example.com, enter blog. If you leave this field blank, the default record name is the
        name of the domain.
      </p>
    ),
  },
  "record-type": {
    title: "Record type",
    body: (
      <p>
        The DNS type of the record determines the format of the value that Route 53 returns in
        response to DNS queries.
      </p>
    ),
    learnMore: [{ text: "Supported DNS record types", href: `${DOCS}/ResourceRecordTypes.html` }],
  },
  "record-value": {
    title: "Value/Route traffic to",
    body: (
      <p>
        The option that you choose determines how Route 53 responds to DNS queries. For most
        options, you specify where you want to route internet traffic. Enter multiple values on
        separate lines.
      </p>
    ),
  },
  ttl: {
    title: "TTL (seconds)",
    body: (
      <p>
        The amount of time, in seconds, that DNS resolvers and web browsers cache the settings in
        this record. (&quot;TTL&quot; means &quot;time to live.&quot;) This value does not apply to
        alias records.
      </p>
    ),
  },
  "routing-policy": {
    title: "Routing policy",
    body: (
      <p>
        The routing policy determines how Amazon Route 53 responds to queries. Simple routing
        returns the same response to every client; the other policies choose a response by weight,
        location, latency or health.
      </p>
    ),
    learnMore: [{ text: "Choosing a routing policy", href: `${DOCS}/routing-policy.html` }],
  },
  "import-zone-file": {
    title: "Import zone file",
    body: (
      <>
        <p>
          You can create records for a Route 53 hosted zone by importing a zone file in RFC 1035
          (BIND) format.
        </p>
        <p>
          The NS and SOA records for the zone itself are ignored, because Route 53 creates them with
          the hosted zone. $ORIGIN and $TTL directives are supported.
        </p>
      </>
    ),
    learnMore: [
      {
        text: "Creating records by importing a zone file",
        href: `${DOCS}/resource-record-sets-creating-import.html`,
      },
    ],
  },
  dnssec: {
    title: "DNSSEC signing",
    body: (
      <>
        <p>
          When you enable DNSSEC signing on a hosted zone, Route 53 cryptographically signs each
          record in that hosted zone, so that resolvers can verify that DNS responses came from
          Route 53 and were not tampered with.
        </p>
        <p>
          Route 53 manages the zone-signing key. You manage the key-signing key (KSK), which is
          based on a customer managed key in AWS Key Management Service.
        </p>
      </>
    ),
    learnMore: [
      { text: "Configuring DNSSEC signing", href: `${DOCS}/dns-configuring-dnssec.html` },
    ],
  },
  "accelerated-recovery": {
    title: "Accelerated recovery",
    body: (
      <p>
        Accelerated recovery lets you continue to make changes to the records of a public hosted
        zone after an impairment to the US East (N. Virginia) Region, where the Route 53 control
        plane runs.
      </p>
    ),
  },
  "coming-soon": {
    title: "Coming soon",
    body: (
      <p>
        This section of the console is not part of this clone. Hosted zones and records are fully
        functional.
      </p>
    ),
  },
} satisfies Record<string, HelpTopic>;

export type HelpTopicId = keyof typeof helpTopics;
