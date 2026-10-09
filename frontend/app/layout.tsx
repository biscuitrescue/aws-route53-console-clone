import "@cloudscape-design/global-styles/index.css";
import "@fontsource-variable/ubuntu-sans/wght.css";
import "@fontsource-variable/ubuntu-sans/wght-italic.css";
import "./theme.generated.css";
import "./globals.css";

import type { Metadata } from "next";

import { visualModeBootScript } from "@/hooks/use-visual-mode";

import { Providers } from "./providers";

export const metadata: Metadata = {
  title: "Route 53",
  description: "A clone of the Amazon Route 53 console, not affiliated with AWS.",
  robots: { index: false, follow: false },
};

export default function RootLayout({ children }: LayoutProps<"/">) {
  return (
    <html lang="en">
      {/* The boot script may add the dark-mode class before React hydrates. */}
      <body suppressHydrationWarning>
        <script dangerouslySetInnerHTML={{ __html: visualModeBootScript }} />
        <Providers>{children}</Providers>
      </body>
    </html>
  );
}
