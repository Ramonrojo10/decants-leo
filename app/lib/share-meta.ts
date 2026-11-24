import { CLASSES, STEPS, decodeBuild, encodeBuild, optionOf } from "../data/builder";
import { SITE_URL } from "./site";

/** Si la URL trae un ?arma= válido, devuelve la imagen/título para compartir ese armado. */
export function sharedBuildMeta(arma: string | string[] | undefined) {
  const build = decodeBuild(typeof arma === "string" ? arma : null);
  if (!build) return null;
  const key = encodeBuild(build);
  const label = CLASSES.find((c) => c.id === build.cls)!.label;
  const parts = STEPS[build.cls].map((s) => optionOf(build.cls, s.id, build.parts[s.id]!).name.toLowerCase());
  const alt = `Seiko Mod ${label} armado: ${parts.join(", ")}`;
  return {
    title: `Mi Seiko Mod ${label} · Decants Leo`,
    image: { url: `${SITE_URL}/api/og?arma=${encodeURIComponent(key)}`, width: 1200, height: 630, alt },
  };
}

/** Sobrescribe solo título e imagen social; el resto de la metadata queda igual. */
export function withSharedBuild<T extends { openGraph: object; twitter: object }>(
  base: T,
  arma: string | string[] | undefined,
): T {
  const shared = sharedBuildMeta(arma);
  if (!shared) return base;
  return {
    ...base,
    openGraph: { ...base.openGraph, title: shared.title, images: [shared.image] },
    twitter: { ...base.twitter, title: shared.title, images: [{ url: shared.image.url, alt: shared.image.alt }] },
  };
}
