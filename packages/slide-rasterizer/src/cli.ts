import { createServer, type IncomingMessage, type ServerResponse } from "node:http";
import { copyFileSync, existsSync, mkdirSync, readFileSync, statSync } from "node:fs";
import { dirname, extname, join, relative, resolve, sep } from "node:path";
import { fileURLToPath } from "node:url";
import { chromium } from "playwright";

const STAGE_WIDTH = 1280;
const STAGE_HEIGHT = 720;
const MIME_TYPES: Record<string, string> = {
  ".css": "text/css; charset=utf-8",
  ".html": "text/html; charset=utf-8",
  ".js": "text/javascript; charset=utf-8",
  ".json": "application/json",
  ".map": "application/json",
  ".png": "image/png",
  ".svg": "image/svg+xml",
  ".woff2": "font/woff2",
};

function requiredArg(flag: string): string {
  const index = process.argv.indexOf(flag);
  const value = index >= 0 ? process.argv[index + 1] : undefined;
  if (!value || value.startsWith("--")) {
    throw new Error(`missing ${flag} <path>`);
  }
  return value;
}

function distDir(): string {
  return dirname(fileURLToPath(import.meta.url));
}

function startStaticServer(root: string): Promise<{ origin: string; close: () => Promise<void> }> {
  const server = createServer((request: IncomingMessage, response: ServerResponse) => {
    const url = new URL(request.url ?? "/", "http://127.0.0.1");
    const pathname = url.pathname === "/" ? "/index.html" : decodeURIComponent(url.pathname);
    const filePath = resolve(root, `.${pathname}`);
    const relativePath = relative(root, filePath);
    if (!relativePath || relativePath.startsWith("..") || relativePath.startsWith(sep)) {
      response.writeHead(403);
      response.end("forbidden");
      return;
    }
    try {
      if (!statSync(filePath).isFile()) throw new Error("not a file");
      const body = readFileSync(filePath);
      response.writeHead(200, {
        "content-type": MIME_TYPES[extname(filePath)] ?? "application/octet-stream",
      });
      response.end(body);
    } catch {
      response.writeHead(404);
      response.end("not found");
    }
  });

  return new Promise((resolveListen, reject) => {
    server.once("error", reject);
    server.listen(0, "127.0.0.1", () => {
      const address = server.address();
      if (!address || typeof address === "string") {
        reject(new Error("failed to bind rasterizer static server"));
        return;
      }
      resolveListen({
        origin: `http://127.0.0.1:${address.port}`,
        close: () =>
          new Promise((resolveClose, rejectClose) => {
            server.close((error) => (error ? rejectClose(error) : resolveClose()));
          }),
      });
    });
  });
}

async function rasterize(slidePath: string, outPath: string): Promise<void> {
  const dist = distDir();
  const indexHtml = join(dist, "index.html");
  if (!existsSync(indexHtml)) {
    throw new Error(`missing ${indexHtml}; run npm run build --workspace @gapo-slidegen/slide-rasterizer`);
  }
  mkdirSync(dirname(resolve(outPath)), { recursive: true });
  copyFileSync(resolve(slidePath), join(dist, "slide.json"));

  const server = await startStaticServer(dist);
  const browser = await chromium.launch();
  try {
    const page = await browser.newPage({
      viewport: { width: STAGE_WIDTH, height: STAGE_HEIGHT },
      deviceScaleFactor: 1,
    });
    await page.setViewportSize({ width: STAGE_WIDTH, height: STAGE_HEIGHT });
    await page.goto(`${server.origin}/index.html`, { waitUntil: "networkidle" });
    await page.waitForSelector("canvas");
    await page.locator("canvas").first().screenshot({ path: outPath, type: "png" });
  } finally {
    await browser.close();
    await server.close();
  }

  const png = readFileSync(outPath);
  if (png.byteLength <= 100) {
    throw new Error(`rasterizer wrote an empty png: ${outPath}`);
  }
}

async function main(): Promise<void> {
  await rasterize(requiredArg("--slide"), requiredArg("--out"));
}

main().catch((error: unknown) => {
  console.error(error);
  process.exitCode = 1;
});
