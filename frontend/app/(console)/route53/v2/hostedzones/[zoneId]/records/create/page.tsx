import { CreateRecordPage } from "@/components/records/create-record-page";

export default async function Page({
  params,
}: PageProps<"/route53/v2/hostedzones/[zoneId]/records/create">) {
  const { zoneId } = await params;
  return <CreateRecordPage zoneId={zoneId} />;
}
