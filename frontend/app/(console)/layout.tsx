import { ConsoleFrame } from "@/components/shell/console-frame";

export default function ConsoleLayout({ children }: { children: React.ReactNode }) {
  return <ConsoleFrame>{children}</ConsoleFrame>;
}
