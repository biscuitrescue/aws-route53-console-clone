import { ImportZoneFilePage } from "@/components/records/import-zone-file-page";

export default async function Page({
  params,
}: PageProps<"/route53/v2/hostedzones/[zoneId]/records/import">) {
  const { zoneId } = await params;
  return <ImportZoneFilePage zoneId={zoneId} />;
}
