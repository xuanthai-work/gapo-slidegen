# M1 generation pipeline boundary

Status: local end-to-end foundation implemented; gateway adapter pending

## Flow

1. An authenticated user creates a generation request from an owned source.
2. FastAPI verifies source ownership and enqueues a PostgreSQL `generate` job.
3. A separate worker claims the job with `FOR UPDATE SKIP LOCKED`.
4. The configured presentation provider returns canonical slide JSON.
5. The worker stores the presentation under the same owner and completes the
   job with a presentation id.
6. The dashboard polls job status and opens the persisted document in the web
   editor when generation succeeds.

All job and presentation reads filter by the authenticated owner. The maximum
slide count remains 30 at both the API and canonical schema boundaries.

## Provider boundary

`PresentationProvider` receives normalized source text, sections, language,
slide count, title, and a preallocated presentation id. It returns canonical
presentation JSON and has no dependency on FastAPI, PostgreSQL, or the editor.

The only current provider is `stub`. It deterministically creates native text
and shape elements and sends no data outside the machine. It exists to test the
queue, persistence, polling, and editor-loading path; it is not presented as AI
generation quality.

The company gateway adapter will be implemented after its request format,
structured-output behavior, model list, authentication method, and error
contract are known. A second provider can implement the same protocol later.

## Worker behavior

- Claim and provider execution are separated so the row lock is not held while
  waiting for model output.
- A deleted or wrong-owner source fails the claimed job.
- Provider failures produce a terminal failed job with a bounded error message.
- Successful output is stored in `presentations.document` as canonical JSON.
- A process crash recovery policy for stale running jobs remains future work.

## Local run

After PostgreSQL is running and migrated, run the worker separately:

```bash
npm run worker:dev
```

`SLIDEGEN_GENERATION_PROVIDER=stub` is the safe local default until the gateway
adapter is configured.
