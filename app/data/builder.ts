/**
 * Catálogo del armador de Seiko Mods (base SKX007/SRPD · movimiento NH35).
 *
 * Todas las piezas son productos reales de Namoki Mods (permiso de uso de
 * fotos otorgado). Cada capa en public/builder/parts es la foto del
 * proveedor con el fondo quitado, escalada a su medida real en milímetros y
 * centrada en el eje del reloj (lienzo 1000 px = 48 mm).
 *
 * Las correas usan un lienzo más alto (1000 x 2000 px = 48 x 96 mm) con el
 * mismo eje; el armador las dibuja centradas detrás de la caja.
 *
 * Para agregar una pieza: procesar su foto con las herramientas del armador y
 * sumar una opción aquí. Las capas light-* son solo luz (sombra y reflejo).
 */

export type StepId = "case" | "dial" | "hands" | "bezel" | "strap";

export type PartOption = {
  id: string;
  name: string;
  detail: string;
  /** Capas que esta pieza aporta al reloj (en orden de dibujo). */
  layers: string[];
  /** Imagen para el selector (una de sus capas). */
  thumb: string;
  /** Solo se puede elegir si la pieza elegida en ese paso está en la lista. */
  requires?: Partial<Record<StepId, string[]>>;
  /** Texto que se muestra cuando la pieza no es compatible. */
  requiresNote?: string;
};

export type Step = {
  id: StepId;
  label: string;
  question: string;
  options: PartOption[];
};

export const FAMILY = {
  name: "Base SKX007 · movimiento NH35",
  note: "Piezas reales de Namoki Mods: esfera de 28.5 mm, inserto SKX de 38 mm.",
};

const part = (id: string, name: string, detail: string, layers: string[], thumb = layers[0]): PartOption => ({
  id,
  name,
  detail,
  layers,
  thumb,
});

const caseOpt = (id: string, name: string, ref: string, mm: string) =>
  part(id, name, `Namoki ${ref} · ${mm} mm`, [`case-${id}`]);
const dialOpt = (id: string, name: string) => part(id, name, "Namoki · 28.5 mm", [`dial-${id}`]);
const handsOpt = (id: string, name: string) =>
  part(id, name, "Namoki · compatibles NH35", [`hands-${id}-hour`, `hands-${id}-minute`, `hands-${id}-seconds`], `hands-${id}-minute`);
const insertOpt = (id: string, name: string, material: string) =>
  part(id, name, `Namoki · ${material}, 38 mm`, [`insert-${id}`]);
const strapOpt = (id: string, name: string, material: string) =>
  part(id, name, `Namoki · ${material}, 22 mm`, [`strap-${id}`]);

export const steps: Step[] = [
  {
    id: "case",
    label: "Caja",
    question: "¿Con qué caja empezamos?",
    options: [
      caseOpt("dive-steel", "Dive acero", "NMK942", "42"),
      caseOpt("dive-black", "Dive negro", "NMK942", "42"),
      caseOpt("fathoms-steel", "Fathoms acero", "NMK957", "41"),
      caseOpt("fathoms-rosegold", "Fathoms oro rosa", "NMK957", "41"),
      caseOpt("gmtsub-black", "GMT Sub negro", "NMK941", "40.5"),
      caseOpt("gmtsub-rosegold", "GMT Sub oro rosa", "NMK941", "40.5"),
      caseOpt("sumo-steel", "Sumo acero", "NMK960", "43.8"),
    ],
  },
  {
    id: "dial",
    label: "Esfera",
    question: "¿Qué esfera?",
    options: [
      dialOpt("dj-navy", "DJ azul marino"),
      dialOpt("fume-green", "Fumé verde"),
      dialOpt("fume-blue", "Fumé azul"),
      dialOpt("fathoms-black", "Fathoms negra"),
      dialOpt("iwate-navy", "Iwate azul"),
      dialOpt("enamel-blue", "Esmalte azul"),
      dialOpt("dj-mint", "DJ verde menta"),
      dialOpt("sector-salmon", "Sector salmón"),
      dialOpt("tuxedo", "Tuxedo"),
      dialOpt("ice-forest", "Ice Forest"),
      dialOpt("dj-white", "DJ blanca romana"),
      dialOpt("mop-white", "Nácar blanco"),
    ],
  },
  {
    id: "hands",
    label: "Manecillas",
    question: "¿Qué manecillas?",
    options: [
      handsOpt("fpj-steel", "FPJ acero"),
      handsOpt("fpj-bluesteel", "FPJ acero azulado"),
      handsOpt("fpj-gold", "FPJ oro"),
      handsOpt("fpj-rosegold", "FPJ oro rosa"),
      handsOpt("syringe-blue", "Syringe azul"),
    ],
  },
  {
    id: "bezel",
    label: "Bisel",
    question: "¿Y el bisel?",
    options: [
      insertOpt("pepsi", "GMT Pepsi", "aluminio"),
      insertOpt("coke", "GMT Coke", "aluminio"),
      insertOpt("rootbeer", "GMT Root Beer", "aluminio"),
      insertOpt("bruce-wayne", "Bruce Wayne", "cerámico"),
      insertOpt("batman", "Batman", "cerámico"),
      insertOpt("blue", "Azul", "cerámico"),
      insertOpt("green", "Verde", "cerámico"),
      insertOpt("green-black", "Verde y negro", "cerámico"),
    ],
  },
  {
    id: "strap",
    label: "Correa",
    question: "¿Y la correa?",
    options: [
      strapOpt("curved-black", "Caucho curvo negro", "FKM NMK801 de ajuste exacto"),
      strapOpt("fkm-black", "Caucho FKM negro", "caucho FKM"),
      strapOpt("fkm-navy", "Caucho FKM azul", "caucho FKM"),
      strapOpt("fkm-green", "Caucho FKM verde", "caucho FKM"),
      strapOpt("tropic-black", "Tropic negra", "caucho FKM"),
      strapOpt("tropic-blue", "Tropic azul", "caucho FKM"),
      strapOpt("waffle-black", "Waffle negra", "caucho"),
      strapOpt("leather-brown", "Piel vintage café", "piel"),
      strapOpt("leather-navy", "Piel vintage azul", "piel"),
      strapOpt("pilot-black", "Piel Pilot negra", "piel"),
    ],
  },
];

/** Orden de dibujo (de atrás hacia adelante). Las capas light-* son luz fija. */
export const DRAW_ORDER: Array<StepId | "light-depth" | "light-crystal"> = [
  "strap",
  "case",
  "dial",
  "light-depth",
  "hands",
  "bezel",
  "light-crystal",
];

export type Build = Record<StepId, string>;

export const DEFAULT_BUILD: Build = {
  case: "dive-steel",
  dial: "dj-navy",
  hands: "fpj-steel",
  bezel: "pepsi",
  strap: "curved-black",
};

export function optionOf(step: StepId, id: string) {
  return steps.find((s) => s.id === step)!.options.find((o) => o.id === id)!;
}

export function isAllowed(option: PartOption, build: Build) {
  if (!option.requires) return true;
  return Object.entries(option.requires).every(([step, ids]) =>
    ids!.includes(build[step as StepId]),
  );
}

/** Si un cambio deja piezas incompatibles, las regresa a la primera opción válida. */
export function normalize(build: Build): Build {
  const next = { ...build };
  for (const step of steps) {
    const current = step.options.find((o) => o.id === next[step.id]);
    if (!current || !isAllowed(current, next)) {
      next[step.id] = step.options.find((o) => isAllowed(o, next))!.id;
    }
  }
  return next;
}

export function encodeBuild(build: Build) {
  return steps.map((s) => build[s.id]).join(".");
}

export function decodeBuild(value: string | null): Build | null {
  if (!value) return null;
  const ids = value.split(".");
  if (ids.length !== steps.length) return null;
  const build = { ...DEFAULT_BUILD };
  for (const [i, step] of steps.entries()) {
    if (!step.options.some((o) => o.id === ids[i])) return null;
    build[step.id] = ids[i];
  }
  return normalize(build);
}

export const layerSrc = (layer: string) => `/builder/parts/${layer}.webp`;
