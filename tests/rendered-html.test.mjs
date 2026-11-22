import assert from "node:assert/strict";
import { access, readFile } from "node:fs/promises";
import test from "node:test";

async function render(path = "/") {
  const workerUrl = new URL("../dist/server/index.js", import.meta.url);
  workerUrl.searchParams.set("test", `${process.pid}-${Date.now()}`);
  const { default: worker } = await import(workerUrl.href);

  return worker.fetch(
    new Request(`http://localhost${path}`, {
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
  assert.match(html, /<title>Decants Leo · Seiko Mods en Tijuana \| Arma tu reloj<\/title>/i);
  assert.match(html, /El tiempo,/);
  assert.match(html, /Stock seleccionado/);
  assert.match(html, /Seiko Mods/);
  assert.match(html, /Santos/);
  assert.match(html, /<link rel="canonical" href="https:\/\/decantsleo\.online\/?"/i);
  assert.match(html, /property="og:image" content="https:\/\/decantsleo\.online\/og\.jpg"/i);
  assert.match(html, /<script type="application\/ld\+json">/i);
  assert.match(html, /"@type":\["Organization","Store"\]/);
  assert.match(html, /"telephone":"\+52 665 142 6008"/);
  assert.doesNotMatch(html, /name="keywords"/i);
  const waLinks = [...html.matchAll(/https:\/\/wa\.me\/[^"?]*/g)].map((m) => m[0]);
  assert.ok(waLinks.length > 0);
  for (const link of waLinks) assert.equal(link, "https://wa.me/526651426008");
  assert.doesNotMatch(html, /codex-preview|Your site is taking shape/i);
});

test("keeps licensed audio, catalog assets, and disclosure copy in source", async () => {
  const sources = [
    "../app/page.tsx",
    "../app/components/header.tsx",
    "../app/components/store.tsx",
    "../app/lib/site.ts",
  ];
  const [layout, license, ...files] = await Promise.all([
    readFile(new URL("../app/layout.tsx", import.meta.url), "utf8"),
    readFile(new URL("../public/audio/LICENSE.txt", import.meta.url), "utf8"),
    ...sources.map((path) => readFile(new URL(path, import.meta.url), "utf8")),
  ]);
  const [page, header] = files;
  const source = files.join("\n");

  assert.match(header, /deep-techno-ambience\.mp3/);
  // Music never autoplays: it only starts from the header toggle.
  assert.match(header, /preload="none"/);
  assert.doesNotMatch(header, /autoPlay/);
  assert.match(page, /piezas personalizadas independientes/i);
  assert.match(source, /disponibilidad, especificaciones y precio/i);
  assert.match(source, /wa\.me/);
  assert.match(layout, /locale:\s*"es_MX"/);
  assert.match(license, /Mixkit Stock Music Free License/);

  await Promise.all([
    access(new URL("../public/og.jpg", import.meta.url)),
    access(new URL("../public/products/santos-dumont-seiko-mod.jpg", import.meta.url)),
    access(new URL("../public/brand/instagram-profile.jpg", import.meta.url)),
  ]);
});

const STYLE_PAGES = [
  ["gmt", "Seiko Mod GMT en Tijuana"],
  ["nautilus", "Seiko Mod estilo Nautilus en Tijuana"],
  ["santos", "Seiko Mod estilo Santos en Tijuana"],
];

test("renders the indexable style landing pages", async () => {
  for (const [slug, h1] of STYLE_PAGES) {
    const response = await render(`/${slug}`);
    assert.equal(response.status, 200, slug);
    const html = await response.text();
    assert.match(html, new RegExp(`<h1[^>]*>${h1}</h1>`), slug);
    assert.match(html, new RegExp(`<link rel="canonical" href="https://decantsleo\\.online/${slug}"`), slug);
    assert.match(html, /"@type":"FAQPage"/, slug);
    assert.match(html, /"@type":"BreadcrumbList"/, slug);
    assert.match(html, /id="arma"/, slug);
  }
});

test("lists the style pages in the sitemap", async () => {
  const response = await render("/sitemap.xml");
  assert.equal(response.status, 200);
  const xml = await response.text();
  for (const [slug] of STYLE_PAGES) assert.match(xml, new RegExp(`<loc>https://decantsleo\\.online/${slug}</loc>`));
});
