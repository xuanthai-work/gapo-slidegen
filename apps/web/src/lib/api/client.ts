import { env } from "@/lib/env";

export class ApiError extends Error {
  constructor(
    message: string,
    readonly status: number,
  ) {
    super(message);
  }
}

async function getAccessToken(): Promise<string | undefined> {
  const response = await fetch("/api/auth/token", {
    cache: "no-store",
    credentials: "include",
  });
  if (!response.ok) return undefined;

  const payload = (await response.json()) as { token?: unknown };
  return typeof payload.token === "string" ? payload.token : undefined;
}

async function readErrorMessage(response: Response): Promise<string> {
  const payload: unknown = await response.json().catch(() => undefined);
  if (typeof payload === "object" && payload !== null && "detail" in payload) {
    const detail = (payload as { detail?: unknown }).detail;
    if (typeof detail === "string") return detail;
  }
  return "The request failed";
}

export async function apiFetch<T>(
  path: string,
  init: RequestInit = {},
): Promise<T> {
  // Neon Auth's Better Auth JWT plugin exposes the signed access token at
  // `/token`. The Next.js auth handler proxies this request and keeps the
  // upstream session cookie HttpOnly.
  const accessToken = await getAccessToken();

  const response = await fetch(`${env.NEXT_PUBLIC_API_ORIGIN}${path}`, {
    ...init,
    credentials: "include",
    headers: {
      "Content-Type": "application/json",
      ...(accessToken ? { Authorization: `Bearer ${accessToken}` } : {}),
      ...init.headers,
    },
  });

  if (!response.ok) {
    throw new ApiError(await readErrorMessage(response), response.status);
  }

  if (response.status === 204) {
    return undefined as T;
  }

  return response.json() as Promise<T>;
}
