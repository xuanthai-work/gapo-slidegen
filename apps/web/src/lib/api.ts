export type CurrentUser = {
  id: string;
  email: string;
};

export type StoredSource = {
  id: string;
  kind: "prompt" | "manuscript" | "docx" | "pptx" | "pdf";
  title: string;
  filename: string | null;
  content_type: string | null;
  extracted_text: string;
  sections: Array<{ index: number; title: string; text: string }>;
  requires_ocr: boolean;
  warnings: string[];
};

export type GenerationJob = {
  id: string;
  source_id: string | null;
  job_type: "ingest" | "generate" | "export";
  status: "queued" | "running" | "succeeded" | "failed" | "canceled";
  progress: number;
  result: { presentation_id?: string; provider?: string } | null;
  error_code: string | null;
  error_message: string | null;
};

export type StoredPresentation = {
  id: string;
  title: string;
  document: unknown;
  revision: number;
};

export class ApiError extends Error {
  constructor(
    message: string,
    public readonly status: number,
  ) {
    super(message);
  }
}

export async function apiFetch<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(`/api/backend${path}`, {
    ...init,
    credentials: "include",
    headers: {
      ...(init?.body instanceof FormData ? {} : { "Content-Type": "application/json" }),
      ...init?.headers,
    },
  });

  if (!response.ok) {
    const payload = (await response.json().catch(() => null)) as { detail?: string } | null;
    throw new ApiError(payload?.detail ?? "The request could not be completed.", response.status);
  }

  if (response.status === 204) return undefined as T;
  return (await response.json()) as T;
}
