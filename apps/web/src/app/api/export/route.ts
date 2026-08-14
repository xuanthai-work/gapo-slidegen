import { exportPresentationToPptx } from "@gapo-slidegen/pptx-exporter";
import { parsePresentation } from "@gapo-slidegen/slide-schema";

export const runtime = "nodejs";

function safeDownloadName(title: string): string {
  const normalized = title
    .normalize("NFKD")
    .replace(/[\u0300-\u036f]/g, "")
    .replace(/[^A-Za-z0-9._ -]+/g, "")
    .trim()
    .replace(/\s+/g, "-")
    .slice(0, 120);
  return `${normalized || "presentation"}.pptx`;
}

export async function POST(request: Request): Promise<Response> {
  try {
    const apiBaseUrl = process.env.SLIDEGEN_API_INTERNAL_URL ?? "http://127.0.0.1:8000";
    const cookie = request.headers.get("cookie") ?? "";
    const authResponse = await fetch(`${apiBaseUrl}/v1/auth/me`, {
      headers: { cookie },
      cache: "no-store",
    });
    if (!authResponse.ok) {
      return Response.json({ detail: "Authentication required." }, { status: 401 });
    }

    const rawDocument = await request.text();
    if (new TextEncoder().encode(rawDocument).byteLength > 10 * 1024 * 1024) {
      return Response.json({ detail: "Presentation document is too large." }, { status: 413 });
    }
    const document = parsePresentation(JSON.parse(rawDocument));
    const result = await exportPresentationToPptx(document, {
      author: "Gapo SlideGen",
      company: "Gapo",
      resolveAsset: async (assetId) => {
        const assetResponse = await fetch(`${apiBaseUrl}/v1/assets/${assetId}/content`, {
          headers: { cookie },
          cache: "no-store",
        });
        if (!assetResponse.ok) return null;
        const contentType = assetResponse.headers.get("content-type") ?? "application/octet-stream";
        const data = Buffer.from(await assetResponse.arrayBuffer()).toString("base64");
        return { data: `data:${contentType};base64,${data}` };
      },
    });
    return new Response(new Uint8Array(result.buffer), {
      headers: {
        "Content-Type":
          "application/vnd.openxmlformats-officedocument.presentationml.presentation",
        "Content-Disposition": `attachment; filename="${safeDownloadName(document.title)}"`,
        "Cache-Control": "no-store",
        "X-Export-Warnings": String(result.warnings.length),
      },
    });
  } catch (error) {
    const detail = error instanceof Error ? error.message : "Invalid presentation document.";
    return Response.json({ detail }, { status: 422 });
  }
}
