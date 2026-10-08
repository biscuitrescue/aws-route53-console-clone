/**
 * A wordmark in the spirit of the console's logo: lowercase letters over a curved arrow.
 * It is drawn here rather than copied, and it uses `currentColor` so it works on dark and
 * light backgrounds.
 */
export function Logo({ height = 20 }: { height?: number }) {
  return (
    <svg
      xmlns="http://www.w3.org/2000/svg"
      viewBox="0 0 66 40"
      height={height}
      role="img"
      aria-label="Route 53 clone"
      focusable="false"
    >
      <text
        x="33"
        y="24"
        textAnchor="middle"
        fontFamily="'Open Sans', 'Helvetica Neue', Arial, sans-serif"
        fontSize="27"
        fontWeight="700"
        letterSpacing="-1"
        fill="currentColor"
      >
        r53
      </text>
      <path
        d="M8 31c14 8 34 8 49 0"
        fill="none"
        stroke="#ff9900"
        strokeWidth="3.2"
        strokeLinecap="round"
      />
      <path
        d="M52 28.5l6 2-3.4 5"
        fill="none"
        stroke="#ff9900"
        strokeWidth="3.2"
        strokeLinecap="round"
        strokeLinejoin="round"
      />
    </svg>
  );
}
