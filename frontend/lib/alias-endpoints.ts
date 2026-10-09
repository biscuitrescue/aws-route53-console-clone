/** What an alias record can point at, in the order of the console's "Choose endpoint" list. */
export interface AliasEndpoint {
  value: string;
  label: string;
  /** Hosted zone ID of the service, where it is the same in every Region. */
  hostedZoneId?: string;
}

/** The one endpoint the clone can resolve itself: a record of the same hosted zone. */
export const ZONE_RECORD_ENDPOINT = "zone-record";

export const aliasEndpoints: AliasEndpoint[] = [
  { value: ZONE_RECORD_ENDPOINT, label: "Alias to another record in this hosted zone" },
  { value: "api-gateway", label: "Alias to API Gateway API" },
  { value: "apprunner", label: "Alias to AppRunner service" },
  { value: "appsync", label: "Alias to AppSync Domain Name" },
  {
    value: "cloudfront",
    label: "Alias to CloudFront distribution",
    hostedZoneId: "Z2FDTNDATAQYW2",
  },
  { value: "elastic-beanstalk", label: "Alias to Elastic Beanstalk environment" },
  { value: "load-balancer", label: "Alias to Application and Classic Load Balancer" },
  { value: "network-load-balancer", label: "Alias to Network Load Balancer" },
  {
    value: "global-accelerator",
    label: "Alias to Global Accelerator",
    hostedZoneId: "Z2BJ6XQ5FK7U4H",
  },
  { value: "lightsail", label: "Alias to LightSail container service" },
  { value: "opensearch", label: "Alias to OpenSearch domain endpoint" },
  { value: "s3-website", label: "Alias to S3 website endpoint" },
  { value: "vpc-endpoint", label: "Alias to VPC endpoint" },
  { value: "vpc-lattice", label: "Alias to VPC Lattice service" },
];

export function aliasEndpoint(value: string): AliasEndpoint | undefined {
  return aliasEndpoints.find((endpoint) => endpoint.value === value);
}

/**
 * The endpoint an existing alias target belongs to, as far as its hosted zone ID tells:
 * a record of the same zone, or a service with one global hosted zone ID.
 */
export function endpointForTarget(targetZoneId: string, ownZoneId: string): string {
  if (targetZoneId === ownZoneId) return ZONE_RECORD_ENDPOINT;
  return aliasEndpoints.find((endpoint) => endpoint.hostedZoneId === targetZoneId)?.value ?? "";
}
