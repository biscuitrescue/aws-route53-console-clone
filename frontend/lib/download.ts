/** Start a file download from a same-origin URL that answers with `Content-Disposition: attachment`. */
export function downloadFrom(url: string) {
  const anchor = document.createElement("a");
  anchor.href = url;
  anchor.download = "";
  document.body.appendChild(anchor);
  anchor.click();
  anchor.remove();
}

export function zoneExportUrl(zoneId: string, format: "bind" | "json"): string {
  return `/api/v1/hostedzones/${encodeURIComponent(zoneId)}/export?format=${format}`;
}
