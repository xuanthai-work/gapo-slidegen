import type { NextConfig } from "next";
import { loadEnvConfig } from "@next/env";
import path from "node:path";

// Keep one root .env shared by the Next.js and FastAPI workspaces.
loadEnvConfig(
  path.resolve(import.meta.dirname, "../.."),
  process.env.NODE_ENV !== "production",
  console,
  true,
);

const nextConfig: NextConfig = {
  reactStrictMode: true,
  transpilePackages: ["@gapo-slidegen/contracts"],
};

export default nextConfig;
