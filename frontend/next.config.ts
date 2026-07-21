import type { NextConfig } from "next";

const internalApi =
  process.env.INTERNAL_API_URL ||
  process.env.AGENTHINK_API_URL ||
  "http://127.0.0.1:8000";

const nextConfig: NextConfig = {
  output: "standalone",
  async rewrites() {
    return [
      {
        source: "/api/:path*",
        destination: `${internalApi.replace(/\/$/, "")}/api/:path*`,
      },
    ];
  },
};

export default nextConfig;
