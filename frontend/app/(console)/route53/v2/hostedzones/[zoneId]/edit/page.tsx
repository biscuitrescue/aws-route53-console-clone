import { EditZonePage } from "@/components/zones/edit-zone-page";

export default async function Page({ params }: PageProps<"/route53/v2/hostedzones/[zoneId]/edit">) {
  const { zoneId } = await params;
  return <EditZonePage zoneId={zoneId} />;
}
