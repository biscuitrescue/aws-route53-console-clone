/**
 * Icons of the console's navigation bar and footer that Cloudscape's icon set does not
 * include. Shapes are taken from the console's markup; all of them use `currentColor`.
 */
import type { ReactNode } from "react";

function Glyph({
  viewBox,
  size = 16,
  filled = false,
  children,
}: {
  viewBox: string;
  size?: number;
  filled?: boolean;
  children: ReactNode;
}) {
  return (
    <svg
      xmlns="http://www.w3.org/2000/svg"
      viewBox={viewBox}
      width={size}
      height={size}
      fill={filled ? "currentColor" : "none"}
      stroke={filled ? "none" : "currentColor"}
      aria-hidden="true"
      focusable="false"
    >
      {children}
    </svg>
  );
}

const HEXAGON =
  "M14.22 3.41L8.87 0.32C8.63 0.18 8.32 0.11 8 0.11C7.68 0.11 7.37 0.18 7.13 0.32L1.78 3.41C1.3 3.68 0.91 4.36 0.91 4.91V11.09C0.91 11.64 1.3 12.31 1.78 12.59L7.14 15.68C7.38 15.82 7.69 15.89 8.01 15.89C8.33 15.89 8.64 15.82 8.88 15.68L14.24 12.59C14.72 12.31 15.11 11.64 15.11 11.09V4.91C15.11 4.36 14.72 3.68 14.24 3.41H14.22ZM8 13.88L2.91 10.94V5.06L8 2.12L13.09 5.06V9.78L10 8V7.26C10 7 9.86 6.77 9.64 6.64L8.36 5.9C8.25 5.84 8.12 5.8 8 5.8C7.88 5.8 7.75 5.83 7.64 5.9L6.36 6.64C6.14 6.77 6 7.01 6 7.26V8.74C6 9 6.14 9.23 6.36 9.36L7.64 10.1C7.75 10.16 7.88 10.2 8 10.2C8.12 10.2 8.25 10.17 8.36 10.1L9 9.73L12.09 11.51L8 13.87V13.88Z";

/** The assistant's hexagon, as shown inside the search field. */
export function AssistantGlyph() {
  return (
    <Glyph viewBox="0 0 16 16" filled>
      <path d={HEXAGON} />
    </Glyph>
  );
}

/** The assistant's button: the hexagon on a rounded gradient tile. */
export function AssistantTile() {
  return (
    <svg
      xmlns="http://www.w3.org/2000/svg"
      viewBox="0 0 24 24"
      width={24}
      height={24}
      aria-hidden="true"
      focusable="false"
    >
      <defs>
        <radialGradient
          id="assistant-tile-gradient"
          cx="0"
          cy="0"
          r="1"
          gradientUnits="userSpaceOnUse"
          gradientTransform="translate(26.1421 -2.14213) rotate(135) scale(40 51.1797)"
        >
          <stop stopColor="#0073bb" />
          <stop offset="0.3" stopColor="#0f43c9" />
          <stop offset="0.45" stopColor="#2912d5" />
          <stop offset="0.6" stopColor="#3a0bc0" />
          <stop offset="0.8" stopColor="#4a0080" />
        </radialGradient>
      </defs>
      <rect width="24" height="24" rx="6" fill="url(#assistant-tile-gradient)" />
      <path fill="#ffffff" transform="translate(4 4)" d={HEXAGON} />
    </svg>
  );
}

/** Nine squares: the services menu. */
export function ServicesGlyph() {
  return (
    <Glyph viewBox="0 0 16 16" filled>
      {[0, 6, 12].flatMap((x) =>
        [0, 6, 12].map((y) => <rect key={`${x}-${y}`} x={x} y={y} width="4" height="4" rx="1" />),
      )}
    </Glyph>
  );
}

/** Visual mode: follow the browser. */
export function MonitorGlyph() {
  return (
    <Glyph viewBox="-1 -1 14 14">
      <path d="M1 0.5H11C11.2761 0.5 11.5 0.723857 11.5 1V8.59961C11.5 8.87575 11.2761 9.09961 11 9.09961H1C0.723858 9.09961 0.5 8.87575 0.5 8.59961V1C0.5 0.723858 0.723857 0.5 1 0.5Z" />
      <path d="M2.99805 11.2998H8.99805C9.05315 11.2998 9.09842 11.3444 9.09863 11.3994C9.09863 11.4546 9.05328 11.5 8.99805 11.5H2.99805C2.943 11.4998 2.89844 11.4545 2.89844 11.3994C2.8986 11.358 2.92397 11.3227 2.95996 11.3076L2.99805 11.2998Z" />
      <path d="M3.03613 7.1748H5.36133C5.43709 7.17502 5.49805 7.23669 5.49805 7.3125C5.49794 7.38822 5.43702 7.44999 5.36133 7.4502H3.03613C2.96026 7.4502 2.89854 7.38835 2.89844 7.3125C2.89844 7.25554 2.93306 7.20641 2.98242 7.18555L3.03613 7.1748Z" />
    </Glyph>
  );
}

/** Visual mode: light. */
export function SunGlyph() {
  return (
    <Glyph viewBox="0 0 12 12">
      <path d="M5.99121 12V10" />
      <path d="M5.99121 2L5.99121 1.19209e-07" />
      <path d="M11.9951 6.00391L9.99609 6.00391" />
      <path d="M1.99902 6.00391L0 6.00391" />
      <path d="M10.2412 1.75977L8.8277 3.17399" />
      <path d="M3.17285 8.83008L1.75934 10.2443" />
      <path d="M1.75879 1.75391L3.1723 3.16813" />
      <path d="M8.8252 8.82422L10.2387 10.2384" />
      <path d="M5.99219 3.5C7.37164 3.50026 8.49023 4.61922 8.49023 6C8.49023 7.38078 7.37164 8.49974 5.99219 8.5C4.61251 8.5 3.49316 7.38094 3.49316 6C3.49316 4.61906 4.61251 3.5 5.99219 3.5Z" />
    </Glyph>
  );
}

/** Visual mode: dark. */
export function MoonGlyph() {
  return (
    <Glyph viewBox="-1 -1 13 14">
      <path
        strokeWidth="1"
        d="M6.97 0c1.03 0 2 .19 2.88.54C8.09 1.73 6.97 3.51 6.97 5.5c0 2.33 1.53 4.37 3.83 5.51A7.76 7.76 0 0 1 6.97 12C3.12 12 0 9.31 0 6s3.12-6 6.97-6Z"
      />
    </Glyph>
  );
}

export function SignOutGlyph() {
  return (
    <Glyph viewBox="0 0 16 16" filled>
      <path d="M9 0V2H3V14H9V16H3C1.89543 16 1 15.1046 1 14V2C1 0.895431 1.89543 0 3 0H9Z" />
      <path d="M12.5858 9L10 11.5858L11.4142 13L15.7071 8.70711C16.0976 8.31658 16.0976 7.68342 15.7071 7.29289L11.4142 3L10 4.41421L12.5858 7H6V9H12.5858Z" />
    </Glyph>
  );
}

/** The footer's CloudShell mark: a prompt in a rounded square. */
export function CloudShellGlyph() {
  return (
    <Glyph viewBox="0 0 16 16">
      <path
        strokeWidth="2"
        strokeLinecap="round"
        strokeLinejoin="round"
        d="M5 5l2.997 2.998L5 11m4.997-.002H12m3-7.626A2.374 2.374 0 0012.627 1H3.37A2.372 2.372 0 001 3.372v9.256a2.373 2.373 0 002.37 2.373h9.257A2.375 2.375 0 0015 12.628V3.372z"
      />
    </Glyph>
  );
}

export function AgentToolkitGlyph() {
  return (
    <Glyph viewBox="0 0 16 16">
      <rect x="1" y="2" width="14" height="11" rx="1" strokeWidth="2" />
      <line x1="1" y1="5" x2="15" y2="5" />
      <circle cx="8" cy="5" r="2" fill="currentColor" stroke="none" />
    </Glyph>
  );
}
