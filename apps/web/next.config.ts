import type { NextConfig } from "next";

const apiBaseUrl = process.env.SLIDEGEN_API_INTERNAL_URL ?? "http://127.0.0.1:8000";

const nextConfig: NextConfig = {
  transpilePackages: [
    "@gapo-slidegen/slide-editor",
    "@gapo-slidegen/slide-schema",
  ],
  async rewrites() {
    return [
      {
        source: "/api/backend/:path*",
        destination: `${apiBaseUrl}/:path*`,
      },
    ];
  },
};

export default nextConfig;
