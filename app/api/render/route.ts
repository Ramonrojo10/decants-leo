/**
 * Vista realista del armador ("Ver mi reloj realista").
 *
 * Recibe las piezas reales ya armadas (imagen 1000x1000) y pide a Higgsfield
 * una foto realista del mismo reloj puesto en la muñeca de alguien.
 *
 *   POST /api/render
 *   { "build": "dive-steel.dj-navy.fpj-steel.pepsi.curved-black",
 *     "parts": [{ "step": "Caja", "name": "Dive acero", "detail": "..." }, ...],
 *     "image": "data:image/jpeg;base64,..." }
 *
 *   200 → { "imageUrl": "https://..." }
 *   4xx/5xx → { "error": "mensaje para el cliente" }
 *
 * Variables de entorno del servidor (nunca en el navegador):
 *   HF_CREDENTIALS     "key-id:key-secret" de console.higgsfield.ai (en .env.local,
 *                      ignorado por git; en el VPS, como variable del proyecto)
 *   HIGGSFIELD_MODEL   ruta del modelo (por defecto "alibaba/qwen-image-3/edit")
 *
 * Flujo de la API (docs.higgsfield.ai): subir la imagen con
 * /files/generate-upload-url, mandar la generación con su URL pública en
 * `image_urls`, y consultar /requests/{id}/status hasta "completed".
 * Cada armado se genera UNA sola vez: la foto se descarga y se guarda en disco
 * (RENDERS_DIR, por defecto ./data/renders/<build>.<estilo>.png) y se sirve desde
 * GET /api/render?build=<build>. Sobrevive reinicios y no depende de que
 * Higgsfield conserve su enlace. En Docker, RENDERS_DIR debe ser un volumen.
 */

const API = "https://api.higgsfield.ai";
const MAX_WAIT_MS = 90_000;

export const RENDER_PROMPT =
  "Photorealistic lifestyle photograph of the exact watch shown in the reference image being worn on a man's left wrist, as if he is trying it on: strap buckled around the wrist, forearm resting naturally, the other hand lightly adjusting the case or strap, slightly angled view so the case side and crown are visible and the dial is clearly readable and in sharp focus. Keep every part identical to the reference: the case shape and finish, the bezel insert with its numerals and colors, the dial with the same logo, text, markers and date window, the hands at the same positions, and the same strap material, color and texture. Add only real photographic qualities: a sapphire crystal with a soft reflection, depth between dial and bezel, metal texture catching the light. Warm natural light, softly blurred dark background, shallow depth of field. Only the wrist, forearm and hands are visible, no face, no other watches or jewelry, do not add or change any text or parts.";

/** Cambia cuando cambie el estilo de la foto: las vistas guardadas de otro estilo no se reutilizan. */
const RENDER_STYLE = "wrist";

const pending = new Map<string, Promise<string>>();
const BUILD_RE = /^[a-z0-9-]+(\.[a-z0-9-]+){0,9}$/;

type Fs = typeof import("node:fs/promises");
let fsPromise: Promise<Fs | null> | null = null;
function fs() {
  fsPromise ??= import("node:fs/promises").catch(() => null);
  return fsPromise;
}
const rendersDir = () => env("RENDERS_DIR") ?? "./data/renders";
const fileOf = (build: string) => `${rendersDir()}/${build}.${RENDER_STYLE}.png`;
const servedUrl = (build: string) => `/api/render?build=${encodeURIComponent(build)}&style=${RENDER_STYLE}`;

async function savedExists(build: string) {
  const f = await fs();
  if (!f) return false;
  try {
    await f.access(fileOf(build));
    return true;
  } catch {
    return false;
  }
}

async function saveRender(build: string, remoteUrl: string) {
  const f = await fs();
  if (!f) return remoteUrl; // sin disco: se usa el enlace de Higgsfield
  const response = await fetch(remoteUrl);
  if (!response.ok) throw new Error(`Descarga del render falló (${response.status})`);
  await f.mkdir(rendersDir(), { recursive: true });
  await f.writeFile(fileOf(build), new Uint8Array(await response.arrayBuffer()));
  return servedUrl(build);
}

/** Sirve una foto ya guardada. */
export async function GET(request: Request) {
  const build = new URL(request.url).searchParams.get("build") ?? "";
  const f = await fs();
  if (!BUILD_RE.test(build) || !f) return new Response("No encontrado", { status: 404 });
  try {
    const bytes = await f.readFile(fileOf(build));
    return new Response(bytes, {
      headers: { "content-type": "image/png", "cache-control": "public, max-age=31536000, immutable" },
    });
  } catch {
    return new Response("No encontrado", { status: 404 });
  }
}

function env(name: string) {
  const value = (globalThis as { process?: { env?: Record<string, string | undefined> } }).process?.env?.[name];
  return value && value.trim() ? value.trim() : undefined;
}

async function higgsfield(path: string, init: RequestInit, auth: string) {
  const response = await fetch(path.startsWith("http") ? path : `${API}${path}`, {
    ...init,
    headers: { authorization: auth, "content-type": "application/json", ...(init.headers ?? {}) },
  });
  const body = await response.json().catch(() => null);
  if (!response.ok) throw new Error(`Higgsfield ${response.status}: ${JSON.stringify(body)?.slice(0, 300)}`);
  return body as Record<string, unknown>;
}

async function render(image: string, auth: string, model: string) {
  const match = /^data:(image\/(?:jpeg|png|webp));base64,(.+)$/.exec(image);
  if (!match) throw new Error("Imagen inválida");
  const [, contentType, base64] = match;
  const bytes = Uint8Array.from(atob(base64), (c) => c.charCodeAt(0));

  // 1) subir la imagen armada
  const upload = (await higgsfield("/files/generate-upload-url", {
    method: "POST",
    body: JSON.stringify({ content_type: contentType }),
  }, auth)) as { upload_url: string; public_url: string; upload_headers?: Record<string, string> };
  const put = await fetch(upload.upload_url, {
    method: "PUT",
    headers: upload.upload_headers ?? { "content-type": contentType },
    body: bytes,
  });
  if (!put.ok) throw new Error(`Subida falló (${put.status})`);

  // 2) mandar la generación
  const job = (await higgsfield(`/${model}`, {
    method: "POST",
    body: JSON.stringify({ prompt: RENDER_PROMPT, image_urls: [upload.public_url], aspect_ratio: "1:1" }),
  }, auth)) as { request_id: string; status_url?: string };

  // 3) esperar el resultado
  const statusUrl = job.status_url ?? `${API}/requests/${job.request_id}/status`;
  const started = Date.now();
  while (Date.now() - started < MAX_WAIT_MS) {
    await new Promise((r) => setTimeout(r, 2500));
    const status = (await higgsfield(statusUrl, { method: "GET" }, auth)) as {
      status: string;
      images?: Array<{ url: string }>;
    };
    if (status.status === "completed" && status.images?.[0]?.url) return status.images[0].url;
    if (["failed", "nsfw", "canceled"].includes(status.status)) throw new Error(`Generación ${status.status}`);
  }
  throw new Error("La generación tardó demasiado");
}

export async function POST(request: Request) {
  const credentials = env("HF_CREDENTIALS");
  if (!credentials || !credentials.includes(":")) {
    return Response.json({ error: "La vista realista todavía no está conectada al servidor." }, { status: 501 });
  }

  const payload = (await request.json().catch(() => null)) as { build?: string; image?: string } | null;
  if (!payload?.build || !BUILD_RE.test(payload.build) || !payload.image || payload.image.length > 6_000_000) {
    return Response.json({ error: "Solicitud inválida." }, { status: 400 });
  }

  // Ya se generó antes: se entrega gratis.
  if (await savedExists(payload.build)) return Response.json({ imageUrl: servedUrl(payload.build), cached: true });

  try {
    let job = pending.get(payload.build);
    if (!job) {
      const build = payload.build;
      job = render(payload.image, `Key ${credentials}`, env("HIGGSFIELD_MODEL") ?? "alibaba/qwen-image-3/edit").then(
        (remote) => saveRender(build, remote),
      );
      pending.set(build, job);
    }
    const imageUrl = await job;
    return Response.json({ imageUrl });
  } catch (error) {
    console.error("[render]", error);
    return Response.json({ error: "No se pudo generar la vista. Intenta de nuevo." }, { status: 502 });
  } finally {
    pending.delete(payload.build);
  }
}
