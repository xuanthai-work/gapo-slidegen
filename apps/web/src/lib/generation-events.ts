import { apiFetch, type GenerationJob } from "./api";
import type { GenerationPreviewEvent } from "./generation-preview";

export type JobSlidePayload = {
  stage: string;
  message: string;
  slide_count: number;
  latest_slide?: unknown;
  slides: unknown[] | null;
};

export const TERMINAL_JOB_STATUSES = new Set(["succeeded", "failed", "canceled"]);

export function reconnectDelayMs(failures: number, baseMs = 400, maxMs = 4000): number {
  return Math.min(maxMs, baseMs * 2 ** Math.max(0, failures));
}

export function shouldRetryGenerationStream(
  job: Pick<GenerationJob, "status"> | null,
  failures: number,
  maxFailures = 8,
): boolean {
  if (failures >= maxFailures) {
    return false;
  }
  if (job && TERMINAL_JOB_STATUSES.has(job.status)) {
    return false;
  }
  return true;
}

export type SubscribeGenerationEventsHandlers = {
  jobId: string;
  onProgress: (job: GenerationJob) => void;
  onGeneration: (event: GenerationPreviewEvent) => void;
  onSlide: (payload: JobSlidePayload) => void;
  onDisconnectError?: (message: string) => void;
  fetchJob?: (jobId: string) => Promise<GenerationJob>;
  createSource?: (url: string) => EventSource;
};

export function subscribeGenerationEvents(
  handlers: SubscribeGenerationEventsHandlers,
): () => void {
  const {
    jobId,
    onProgress,
    onGeneration,
    onSlide,
    onDisconnectError,
    fetchJob = (id) => apiFetch<GenerationJob>(`/v1/jobs/${id}`),
    createSource = (url) => new EventSource(url),
  } = handlers;
  const url = `/api/jobs/${jobId}/events`;
  let stopped = false;
  let failures = 0;
  let source: EventSource | null = null;
  let reconnectTimer: ReturnType<typeof setTimeout> | null = null;

  function clearReconnect() {
    if (reconnectTimer !== null) {
      clearTimeout(reconnectTimer);
      reconnectTimer = null;
    }
  }

  function closeSource() {
    source?.close();
    source = null;
  }

  function scheduleReconnect() {
    clearReconnect();
    const delay = reconnectDelayMs(failures);
    failures += 1;
    reconnectTimer = setTimeout(connect, delay);
  }

  function connect() {
    if (stopped) {
      return;
    }
    closeSource();
    source = createSource(url);

    source.addEventListener("progress", (event) => {
      try {
        const job = JSON.parse((event as MessageEvent).data) as GenerationJob;
        failures = 0;
        onProgress(job);
        if (TERMINAL_JOB_STATUSES.has(job.status)) {
          stopped = true;
          clearReconnect();
          closeSource();
        }
      } catch {
        /* ignore malformed SSE */
      }
    });

    source.addEventListener("generation", (event) => {
      try {
        failures = 0;
        onGeneration(JSON.parse((event as MessageEvent).data) as GenerationPreviewEvent);
      } catch {
        /* ignore malformed generation events */
      }
    });

    source.addEventListener("slide", (event) => {
      try {
        onSlide(JSON.parse((event as MessageEvent).data) as JobSlidePayload);
      } catch {
        /* ignore */
      }
    });

    source.addEventListener("error", () => {
      closeSource();
      if (stopped) {
        return;
      }
      void fetchJob(jobId)
        .then((job) => {
          onProgress(job);
          if (!shouldRetryGenerationStream(job, failures)) {
            stopped = true;
            return;
          }
          scheduleReconnect();
        })
        .catch(() => {
          if (!shouldRetryGenerationStream(null, failures)) {
            stopped = true;
            onDisconnectError?.("Lost connection to the server.");
            return;
          }
          scheduleReconnect();
        });
    });
  }

  connect();

  return () => {
    stopped = true;
    clearReconnect();
    closeSource();
  };
}
