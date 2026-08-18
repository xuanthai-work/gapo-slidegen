import type { NextApiRequest, NextApiResponse } from "next";

const apiBaseUrl = process.env.SLIDEGEN_API_INTERNAL_URL ?? "http://127.0.0.1:8000";

export const config = {
  api: {
    bodyParser: false,
    externalResolver: true,
  },
};

export default async function handler(req: NextApiRequest, res: NextApiResponse) {
  if (req.method !== "GET") {
    res.setHeader("Allow", "GET");
    res.status(405).end("Method Not Allowed");
    return;
  }

  const { jobId } = req.query;
  if (typeof jobId !== "string") {
    res.status(400).json({ detail: "jobId is required." });
    return;
  }

  const cookie = Array.isArray(req.headers.cookie) ? req.headers.cookie[0] : req.headers.cookie;

  try {
    const upstream = await fetch(`${apiBaseUrl}/v1/jobs/${jobId}/events`, {
      method: "GET",
      headers: {
        accept: "text/event-stream",
        ...(cookie ? { cookie } : {}),
      },
      cache: "no-store",
    });

    if (!upstream.ok || upstream.body === null) {
      const text = await upstream.text().catch(() => "Upstream unavailable.");
      res.status(upstream.status === 200 ? 502 : upstream.status).json({ detail: text });
      return;
    }

    res.setHeader("Content-Type", upstream.headers.get("content-type") ?? "text/event-stream; charset=utf-8");
    res.setHeader("Cache-Control", "no-cache");
    res.setHeader("Connection", "keep-alive");
    res.setHeader("X-Accel-Buffering", "no");
    res.status(200);

    const reader = upstream.body.getReader();
    while (true) {
      const { done, value } = await reader.read();
      if (done) break;
      res.write(Buffer.from(value));
      if (typeof (res as unknown as { flush?: () => void }).flush === "function") {
        (res as unknown as { flush: () => void }).flush();
      }
    }
    res.end();
  } catch (error) {
    res.status(502).json({ detail: error instanceof Error ? error.message : "Upstream failed." });
  }
}
