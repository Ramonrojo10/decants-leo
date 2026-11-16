export type Category = "Seiko Mods" | "Relojes" | "Accesorios";

export type Product = {
  id: string;
  name: string;
  category: Category;
  label: string;
  immediate: boolean;
  /** Foto real tomada con teléfono (siempre se muestra en la galería). */
  image: string;
  position: string;
  note: string;
  reference: string;
};

export type GalleryImage = {
  src: string;
  alt: string;
  kind: "studio" | "photo";
  caption: string;
  position: string;
};

/**
 * Renders de estudio por pieza: /products/studio/<id>-front.jpg (portada) y
 * <id>-angle.jpg (segunda vista). Solo se listan los que ya existen.
 */
export const studioRenders: Record<string, { front?: boolean; angle?: boolean }> = {
  "santos-dumont": { front: true, angle: true },
  "gmt-bruce-wayne": { front: true, angle: true },
  "santos-classic": { front: true, angle: true },
  "daytona-rainbow": { front: true, angle: true },
  "big-bang": { front: true, angle: true },
  "santos-full-ice": { front: true, angle: true },
  "octagonal-necklace": { front: true, angle: true },
};

export function galleryOf(product: Product): GalleryImage[] {
  const renders = studioRenders[product.id] ?? {};
  const images: GalleryImage[] = [];
  if (renders.front)
    images.push({
      src: `/products/studio/${product.id}-front.jpg`,
      alt: `${product.name}, render de estudio de frente`,
      kind: "studio",
      caption: "Render de estudio",
      position: "50% 50%",
    });
  if (renders.angle)
    images.push({
      src: `/products/studio/${product.id}-angle.jpg`,
      alt: `${product.name}, render de estudio en otro ángulo`,
      kind: "studio",
      caption: "Render · otro ángulo",
      position: "50% 50%",
    });
  images.push({
    src: product.image,
    alt: `${product.name}, foto real del inventario`,
    kind: "photo",
    caption: "Foto real",
    position: product.position,
  });
  return images;
}

export function coverOf(product: Product) {
  return galleryOf(product)[0];
}

export const products: Product[] = [
  {
    id: "santos-dumont",
    name: "Santos Dumont",
    category: "Seiko Mods",
    label: "Entrega inmediata",
    immediate: true,
    image: "/products/santos-dumont-seiko-mod.jpg",
    position: "45% 60%",
    note: "Diseño rectangular, esfera clara y correa de piel negra.",
    reference: "Mod personalizado con movimiento Seiko",
  },
  {
    id: "gmt-bruce-wayne",
    name: "GMT Bruce Wayne",
    category: "Seiko Mods",
    label: "Entrega inmediata",
    immediate: true,
    image: "/products/gmt-bruce-wayne-seiko-mod.jpg",
    position: "50% 40%",
    note: "Bisel GMT bicolor y brazalete estilo jubilee.",
    reference: "Mod personalizado con movimiento Seiko",
  },
  {
    id: "santos-classic",
    name: "Santos Classic",
    category: "Seiko Mods",
    label: "Disponible",
    immediate: true,
    image: "/products/santos-seiko-mod.jpg",
    position: "50% 30%",
    note: "Acero, números romanos y una silueta limpia.",
    reference: "Mod personalizado con movimiento Seiko",
  },
  {
    id: "daytona-rainbow",
    name: "Daytona Rainbow",
    category: "Seiko Mods",
    label: "Pieza especial",
    immediate: true,
    image: "/products/daytona-rainbow-seiko-mod.jpg",
    position: "50% 45%",
    note: "Cronógrafo visual con bisel multicolor y acabado bicolor.",
    reference: "Mod personalizado con movimiento Seiko",
  },
  {
    id: "big-bang",
    name: "Big Bang",
    category: "Seiko Mods",
    label: "Entrega inmediata",
    immediate: true,
    image: "/products/big-bang-seiko-mod.jpg",
    position: "50% 45%",
    note: "Caja deportiva, correa de caucho y presencia contundente.",
    reference: "Mod personalizado con movimiento Seiko",
  },
  {
    id: "santos-full-ice",
    name: "Santos Full Ice",
    category: "Relojes",
    label: "Consultar disponibilidad",
    immediate: false,
    image: "/products/santos-full-ice.jpg",
    position: "50% 50%",
    note: "Acabado brillante y esfera negra de alto contraste.",
    reference: "Pieza de catálogo · especificaciones por confirmar",
  },
  {
    id: "octagonal-necklace",
    name: "Octagonal Necklace",
    category: "Accesorios",
    label: "Disponible",
    immediate: true,
    image: "/products/octagonal-necklace.jpg",
    position: "62% 72%",
    note: "Accesorio de cuello con caja octagonal y acabado monocromático.",
    reference: "Accesorio inspirado · marca independiente",
  },
];
