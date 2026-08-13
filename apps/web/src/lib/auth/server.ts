import { createNeonAuth } from "@neondatabase/auth/next/server";

function requiredEnv(name: "NEON_AUTH_BASE_URL" | "NEON_AUTH_COOKIE_SECRET") {
  const value = process.env[name]?.trim();
  if (!value) {
    throw new Error(`${name} is required. Configure it in the repository root .env file.`);
  }
  return value;
}

export const auth = createNeonAuth({
  baseUrl: requiredEnv("NEON_AUTH_BASE_URL"),
  cookies: {
    secret: requiredEnv("NEON_AUTH_COOKIE_SECRET"),
  },
});
