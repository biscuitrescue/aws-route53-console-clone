import type { NextConfig } from "next";

// Where the FastAPI backend listens. The browser never calls it directly: every /api
// request is proxied through this origin, so the session cookie stays first-party.
// Rewrites are resolved at build time, so set BACKEND_URL when building the image.
const backendUrl = process.env.BACKEND_URL ?? "http://127.0.0.1:8000";

const nextConfig: NextConfig = {
  output: "standalone",
  poweredByHeader: false,
  agentRules: false,
  transpilePackages: ["@cloudscape-design/components", "@cloudscape-design/component-toolkit"],
  async rewrites() {
    return [{ source: "/api/:path*", destination: `${backendUrl}/api/:path*` }];
  },
};

export default nextConfig;
