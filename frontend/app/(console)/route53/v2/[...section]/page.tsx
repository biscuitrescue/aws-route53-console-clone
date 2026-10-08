import { notFound } from "next/navigation";

import { ComingSoon } from "@/components/common/coming-soon";
import { placeholderSections } from "@/lib/navigation";

export function generateStaticParams() {
  return placeholderSections.map((section) => ({ section: section.slug.split("/") }));
}

export default async function PlaceholderPage({ params }: PageProps<"/route53/v2/[...section]">) {
  const { section: segments } = await params;
  const section = placeholderSections.find((candidate) => candidate.slug === segments.join("/"));
  if (!section) notFound();
  return <ComingSoon section={section} />;
}
