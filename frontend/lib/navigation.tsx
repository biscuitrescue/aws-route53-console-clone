import Box from "@cloudscape-design/components/box";
import type { SideNavigationProps } from "@cloudscape-design/components/side-navigation";

import { routes } from "./routes";

/** A console section that is not part of the clone and shows a "Coming soon" page. */
export interface PlaceholderSection {
  /** Path segments under /route53/v2. */
  slug: string;
  title: string;
  /** Breadcrumb group the page sits under, when the navigation nests it. */
  group?: string;
  description: string;
}

export const placeholderSections: PlaceholderSection[] = [
  {
    slug: "home",
    title: "Dashboard",
    description:
      "An overview of DNS management, availability monitoring, traffic management and domain registration.",
  },
  {
    slug: "healthchecks",
    title: "Health checks",
    description:
      "Route 53 health checks monitor the health and performance of your application's servers and endpoints.",
  },
  {
    slug: "profiles",
    title: "Profiles",
    description:
      "Profiles let you apply and manage DNS-related Route 53 configurations across many VPCs and accounts.",
  },
  {
    slug: "global-resolver/resolvers",
    title: "Global resolvers",
    group: "Global Resolver",
    description:
      "Global resolvers answer DNS queries from clients anywhere over anycast endpoints.",
  },
  {
    slug: "global-resolver/dns-views",
    title: "Shared DNS views",
    group: "Global Resolver",
    description: "DNS views give groups of clients their own resolution rules.",
  },
  {
    slug: "resolver/vpcs",
    title: "VPCs",
    group: "VPC Resolver",
    description: "Resolver configuration for each of your VPCs.",
  },
  {
    slug: "resolver/inbound-endpoints",
    title: "Inbound endpoints",
    group: "VPC Resolver",
    description:
      "Inbound endpoints let DNS resolvers on your network forward queries to Route 53 Resolver.",
  },
  {
    slug: "resolver/outbound-endpoints",
    title: "Outbound endpoints",
    group: "VPC Resolver",
    description:
      "Outbound endpoints let Route 53 Resolver forward queries to resolvers on your network.",
  },
  {
    slug: "resolver/rules",
    title: "Rules",
    group: "VPC Resolver",
    description: "Rules determine which queries are forwarded and where.",
  },
  {
    slug: "resolver/query-logging",
    title: "Query logging",
    group: "VPC Resolver",
    description: "Query logging records the DNS queries that originate in your VPCs.",
  },
  {
    slug: "resolver/outposts",
    title: "Outposts",
    group: "VPC Resolver",
    description: "Resolver endpoints on AWS Outposts.",
  },
  {
    slug: "domains/registered",
    title: "Registered domains",
    group: "Domains",
    description: "Domains registered or transferred to Route 53.",
  },
  {
    slug: "domains/requests",
    title: "Requests",
    group: "Domains",
    description: "The status of domain registration and transfer requests.",
  },
  {
    slug: "cidr-collections",
    title: "CIDR collections",
    group: "IP-based routing",
    description: "CIDR collections group IP address ranges for IP-based routing.",
  },
  {
    slug: "trafficflow/policies",
    title: "Traffic policies",
    group: "Traffic flow",
    description:
      "Create sophisticated routing configurations for your resources using existing routing types.",
  },
  {
    slug: "trafficflow/policy-records",
    title: "Policy records",
    group: "Traffic flow",
    description: "Policy records apply a traffic policy to a domain or subdomain name.",
  },
];

export function placeholderHref(section: PlaceholderSection): string {
  return `/route53/v2/${section.slug}`;
}

/** The small "New" marker the console puts after recently added sections. */
const newBadge = (
  <Box variant="span" color="text-status-info" fontSize="body-s" fontWeight="bold">
    <span style={{ borderBlockEnd: "1px dashed currentColor" }}>New</span>
  </Box>
);

function link(slug: string, isNew = false): SideNavigationProps.Link {
  const section = placeholderSections.find((candidate) => candidate.slug === slug);
  if (!section) throw new Error(`Unknown navigation section: ${slug}`);
  return {
    type: "link",
    text: section.title,
    href: placeholderHref(section),
    ...(isNew && { info: newBadge }),
  };
}

/** The Route 53 side navigation, in the console's order. */
export const navigationItems: SideNavigationProps.Item[] = [
  link("home"),
  { type: "link", text: "Hosted zones", href: routes.hostedZones },
  link("healthchecks"),
  link("profiles"),
  {
    type: "section",
    text: "Global Resolver",
    items: [link("global-resolver/resolvers", true), link("global-resolver/dns-views", true)],
  },
  {
    type: "section",
    text: "VPC Resolver",
    items: [
      link("resolver/vpcs"),
      link("resolver/inbound-endpoints"),
      link("resolver/outbound-endpoints"),
      link("resolver/rules"),
      link("resolver/query-logging"),
      link("resolver/outposts"),
    ],
  },
  {
    type: "section",
    text: "Domains",
    items: [link("domains/registered"), link("domains/requests")],
  },
  { type: "section", text: "IP-based routing", items: [link("cidr-collections")] },
  {
    type: "section",
    text: "Traffic flow",
    items: [link("trafficflow/policies"), link("trafficflow/policy-records")],
  },
  { type: "divider" },
  {
    type: "link",
    text: "DNS Firewall",
    href: "https://docs.aws.amazon.com/Route53/latest/DeveloperGuide/resolver-dns-firewall.html",
    external: true,
  },
  {
    type: "link",
    text: "Application Recovery Controller",
    href: "https://docs.aws.amazon.com/r53recovery/latest/dg/what-is-route53-recovery.html",
    external: true,
  },
];
