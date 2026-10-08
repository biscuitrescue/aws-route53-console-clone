/** URL paths of the app, mirroring the Route 53 console. */
export const routes = {
  signIn: "/signin",
  hostedZones: "/route53/v2/hostedzones",
} as const;

/** Name of the httpOnly session cookie set by the backend (R53_SESSION_COOKIE_NAME). */
export const SESSION_COOKIE = "r53_session";
