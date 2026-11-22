const PRODUCTION_HOSTS = new Set(["decantsleo.online", "www.decantsleo.online"]);

/** Solo el dominio de producción es indexable; cualquier otro host (VPS de pruebas, localhost) no. */
export async function GET(request: Request) {
  const host = (request.headers.get("x-forwarded-host") ?? request.headers.get("host") ?? "")
    .split(",")[0]
    .trim()
    .toLowerCase()
    .replace(/:\d+$/, "");
  const body = PRODUCTION_HOSTS.has(host)
    ? "User-agent: *\nAllow: /\nDisallow: /api/\n\nSitemap: https://decantsleo.online/sitemap.xml\n"
    : "User-agent: *\nDisallow: /\n";
  return new Response(body, {
    headers: { "content-type": "text/plain; charset=utf-8", "cache-control": "public, max-age=300" },
  });
}
