import { Suspense } from "react";

import { HostedZonesPage } from "@/components/zones/hosted-zones-page";

export default function Page() {
  // The list reads ?search= from the URL, which needs a Suspense boundary to prerender.
  return (
    <Suspense>
      <HostedZonesPage />
    </Suspense>
  );
}
