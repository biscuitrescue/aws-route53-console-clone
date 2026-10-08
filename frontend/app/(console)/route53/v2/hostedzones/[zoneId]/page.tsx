import { ZoneDetailsPage } from "@/components/zones/zone-details-page";

export default async function Page({ params }: PageProps<"/route53/v2/hostedzones/[zoneId]">) {
  const { zoneId } = await params;
  return <ZoneDetailsPage zoneId={zoneId} />;
}
