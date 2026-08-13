import { z } from "zod";

const publicEnvSchema = z.object({
  NEXT_PUBLIC_API_ORIGIN: z.string().url().default("http://localhost:8000"),
});

export const env = publicEnvSchema.parse({
  NEXT_PUBLIC_API_ORIGIN: process.env.NEXT_PUBLIC_API_ORIGIN,
});
