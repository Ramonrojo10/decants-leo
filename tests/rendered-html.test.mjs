import assert from "node:assert/strict";
import { access, readFile } from "node:fs/promises";
import test from "node:test";

async function render() {
  const workerUrl = new URL("../dist/server/index.js", import.meta.url);
  workerUrl.searchParams.set("test", `${process.pid}-${Date.now()}`);
  const { default: worker } = await import(workerUrl.href);

  return worker.fetch(
    new Request("http://localhost/", {
      headers: { accept: "text/html" },
    }),
    {
      ASSETS: {
        fetch: async () => new Response("Not found", { status: 404 }),
      },
    },
    {
      waitUntil() {},
      passThroughOnException() {},
    },
  );
}

test("renders the Decants Leo storefront and production metadata", async () => {
  const response = await render();
  assert.equal(response.status, 200);
  assert.match(response.headers.get("content-type") ?? "", /^text\/html\b/i);

  const html = await response.text();
  assert.match(html, /<html lang="es">/i);
  assert.match(html, /<title>Decants Leo — Relojes y accesorios<\/title>/i);
  assert.match(html, /El tiempo,/);
  assert.match(html, /Stock seleccionado/);
  assert.match(html, /Seiko Mods/);
  assert.match(html, /og\.png/);
  assert.doesNotMatch(html, /codex-preview|Your site is taking shape/i);
});

test("keeps licensed audio, catalog assets, and disclosure copy in source", async () => {
  const [page, layout, license] = await Promise.all([
    readFile(new URL("../app/page.tsx", import.meta.url), "utf8"),
    readFile(new URL("../app/layout.tsx", import.meta.url), "utf8"),
    readFile(new URL("../public/audio/LICENSE.txt", import.meta.url), "utf8"),
  ]);

  assert.match(page, /deep-techno-ambience\.mp3/);
  assert.match(page, /activación|permiso|con tu permiso/i);
  assert.match(page, /piezas personalizadas independientes/i);
  assert.match(page, /disponibilidad, especificaciones y precio/i);
  assert.match(page, /wa\.me/);
  assert.match(layout, /locale:\s*"es_MX"/);
  assert.match(license, /Mixkit Stock Music Free License/);

  await Promise.all([
    access(new URL("../public/og.png", import.meta.url)),
    access(new URL("../public/products/santos-dumont-seiko-mod.png", import.meta.url)),
    access(new URL("../public/brand/instagram-profile.png", import.meta.url)),
  ]);
});
