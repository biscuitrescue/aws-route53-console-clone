import "@cloudscape-design/global-styles/index.css";

import type { Metadata } from "next";

import { Providers } from "./providers";

export const metadata: Metadata = {
  title: "Route 53",
  description: "A clone of the Amazon Route 53 console.",
};

export default function RootLayout({ children }: LayoutProps<"/">) {
  return (
    <html lang="en">
      <body>
        <Providers>{children}</Providers>
      </body>
    </html>
  );
}
