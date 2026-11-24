/**
 * Imagen para compartir un armado (WhatsApp, redes): GET /api/og?arma=<armado>
 * Junta las capas reales del armado (mismo orden que el armador) en un JPEG
 * de 1200x630 y lo guarda en disco para servirlo de ahí las siguientes veces.
 */
import { decodeBuild, encodeBuild, layersOf } from "../../data/builder";

const W = 1200;
const H = 630;
const pending = new Map<string, Promise<Uint8Array>>();

const env = (name: string) => {
  const v = (globalThis as { process?: { env?: Record<string, string | undefined> } }).process?.env?.[name];
  return v && v.trim() ? v.trim() : undefined;
};

async function generate(key: string, layerSrcs: string[]) {
  const [{ default: sharp }, fs, path] = await Promise.all([
    import("sharp"),
    import("node:fs/promises"),
    import("node:path"),
  ]);
  const roots = [path.join(process.cwd(), "public"), path.join(process.cwd(), "dist", "client")];
  const read = async (src: string) => {
    for (const root of roots) {
      try {
        return await fs.readFile(path.join(root, src));
      } catch {}
    }
    throw new Error(`Capa no encontrada: ${src}`);
  };

  // Apila las capas en el lienzo 1000x2000 y recorta y=400..1600 (caja + correa arriba y abajo, con fundido a los bordes).
  const buffers = await Promise.all(layerSrcs.map(read));
  const stack = await sharp({
    create: { width: 1000, height: 2000, channels: 4, background: { r: 0, g: 0, b: 0, alpha: 0 } },
  })
    .composite(buffers.map((input) => ({ input })))
    .png()
    .toBuffer();
  const cropH = 1200;
  const targetH = 600;
  const targetW = Math.round((1000 * targetH) / cropH);
  const watch = await sharp(stack)
    .extract({ left: 0, top: 400, width: 1000, height: cropH })
    .resize(targetW, targetH)
    .composite([
      {
        // fundido arriba y abajo: la correa se pierde en el fondo oscuro sin corte seco
        input: Buffer.from(
          `<svg xmlns="http://www.w3.org/2000/svg" width="${targetW}" height="${targetH}"><defs><linearGradient id="f" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="#fff" stop-opacity="0"/><stop offset="0.14" stop-color="#fff"/><stop offset="0.86" stop-color="#fff"/><stop offset="1" stop-color="#fff" stop-opacity="0"/></linearGradient></defs><rect width="100%" height="100%" fill="url(#f)"/></svg>`,
        ),
        blend: "dest-in",
      },
    ])
    .png()
    .toBuffer();

  const glow = Buffer.from(
    `<svg xmlns="http://www.w3.org/2000/svg" width="${W}" height="${H}"><defs><radialGradient id="g" cx="50%" cy="50%" r="55%"><stop offset="0" stop-color="#2a2a2a"/><stop offset="1" stop-color="#050505"/></radialGradient></defs><rect width="100%" height="100%" fill="url(#g)"/></svg>`,
  );
  const jpeg = await sharp(glow)
    .composite([{ input: watch, left: Math.round((W - targetW) / 2), top: Math.round((H - targetH) / 2) }])
    .jpeg({ quality: 82, mozjpeg: true })
    .toBuffer();

  const dir = `${env("RENDERS_DIR") ?? "./data/renders"}/og`;
  try {
    await fs.mkdir(dir, { recursive: true });
    await fs.writeFile(`${dir}/${key}.jpg`, jpeg);
  } catch {}
  return new Uint8Array(jpeg);
}

export async function GET(request: Request) {
  const build = decodeBuild(new URL(request.url).searchParams.get("arma"));
  if (!build) return new Response("No encontrado", { status: 404 });
  const key = encodeBuild(build);
  const headers = { "content-type": "image/jpeg", "cache-control": "public, max-age=31536000, immutable" };

  const fs = await import("node:fs/promises");
  const file = `${env("RENDERS_DIR") ?? "./data/renders"}/og/${key}.jpg`;
  try {
    return new Response(new Uint8Array(await fs.readFile(file)), { headers });
  } catch {}

  try {
    let job = pending.get(key);
    if (!job) {
      job = generate(key, layersOf(build).map((l) => l.src));
      pending.set(key, job);
      job.then(() => pending.delete(key), () => pending.delete(key));
    }
    return new Response(await job, { headers });
  } catch (error) {
    console.error("[og]", error);
    return Response.redirect(new URL("/og.jpg", request.url), 302);
  }
}
