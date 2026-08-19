import { describe, expect, it } from "vitest";
import {
  reconnectDelayMs,
  shouldRetryGenerationStream,
} from "../generation-events";

describe("generation event reconnect policy", () => {
  it("backs off reconnects up to a cap", () => {
    expect(reconnectDelayMs(0, 400, 4000)).toBe(400);
    expect(reconnectDelayMs(1, 400, 4000)).toBe(800);
    expect(reconnectDelayMs(8, 400, 4000)).toBe(4000);
  });

  it("retries only while the job is still running", () => {
    expect(shouldRetryGenerationStream({ status: "running" }, 0)).toBe(true);
    expect(shouldRetryGenerationStream({ status: "succeeded" }, 0)).toBe(false);
    expect(shouldRetryGenerationStream({ status: "failed" }, 1)).toBe(false);
    expect(shouldRetryGenerationStream(null, 8)).toBe(false);
  });
});
