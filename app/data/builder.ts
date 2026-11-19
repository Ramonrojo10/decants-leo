/**
 * Catálogo del armador de Seiko Mods: solo piezas propias de Leo, en dos clases
 * (GMT y Nautilus). Dentro de cada clase todo es combinable.
 *
 * Cada capa de public/builder/leo/<clase> es una pieza real con el fondo
 * quitado, en el mismo lienzo de 1000 x 2000 px (1000 px = 48 mm, centro de la
 * esfera en 500,1000), así que se apilan sin desplazamientos.
 * Se generan con scripts/builder/export_leo_parts.py.
 */

export type ClassId = "gmt" | "nautilus";
export type StepId = "case" | "dial" | "bezel" | "bracelet" | "strap";

export type PartOption = {
  id: string;
  name: string;
  detail: string;
};

export type Step = {
  id: StepId;
  label: string;
  question: string;
  options: PartOption[];
};

export type Build = { cls: ClassId; parts: Partial<Record<StepId, string>> };

export const FAMILY = {
  name: "Seiko Mod · movimiento NH35",
  note: "Piezas reales de Leo · todas combinables dentro de su clase",
};

export const CLASSES: { id: ClassId; label: string; name: string }[] = [
  { id: "gmt", label: "GMT", name: "Clase GMT" },
  { id: "nautilus", label: "Nautilus", name: "Clase Nautilus" },
];

const opt = (cls: ClassId, id: string, name: string): PartOption => ({
  id,
  name,
  detail: `Pieza de Leo · compatible con toda la clase ${cls === "gmt" ? "GMT" : "Nautilus"}`,
});
const list = (cls: ClassId, items: [string, string][]) => items.map(([id, name]) => opt(cls, id, name));

export const STEPS: Record<ClassId, Step[]> = {
  gmt: [
    {
      id: "case",
      label: "Caja",
      question: "¿Con qué caja empezamos?",
      options: list("gmt", [
        ["gmt-02", "Acero"],
        ["gmt-05", "Oro rosa"],
        ["gmt-07", "Bicolor oro rosa"],
      ]),
    },
    {
      id: "dial",
      label: "Esfera",
      question: "¿Qué esfera?",
      options: list("gmt", [
        ["gmt-01", "Aventurina azul · manecillas doradas"],
        ["gmt-02", "Negra · aguja GMT roja"],
        ["gmt-03", "Meteorito · aguja GMT roja"],
        ["gmt-05", "Negra · detalles oro rosa"],
        ["gmt-08", "Negra · aguja GMT azul"],
        ["gmt-09", "Negra · aguja GMT morada"],
        ["gmt-10", "Meteorito · aguja GMT verde"],
        ["gmt-11", "Negra · aguja GMT verde"],
      ]),
    },
    {
      id: "bezel",
      label: "Bisel",
      question: "¿Y el bisel?",
      options: list("gmt", [
        ["gmt-02", "Coke (rojo)"],
        ["gmt-03", "Pepsi (azul y rojo)"],
        ["gmt-01", "Negro y dorado"],
        ["gmt-04", "Negro y gris"],
        ["gmt-05", "Root Beer (café y negro)"],
        ["gmt-08", "Batman (azul y negro)"],
        ["gmt-09", "Morado y negro"],
        ["gmt-11", "Sprite (verde y negro)"],
      ]),
    },
    {
      id: "bracelet",
      label: "Extensible",
      question: "¿Y el extensible?",
      options: list("gmt", [
        ["gmt-02", "Jubilee acero"],
        ["gmt-01", "Jubilee bicolor dorado"],
        ["gmt-07", "Jubilee bicolor oro rosa"],
        ["gmt-08", "Oyster acero"],
        ["gmt-05", "Oyster oro rosa"],
      ]),
    },
  ],
  nautilus: [
    {
      id: "case",
      label: "Caja",
      question: "¿Con qué caja empezamos?",
      // naut-03 (acero), naut-08 (oro rosa), naut-05 (negro PVD): las más limpias
      options: list("nautilus", [
        ["naut-03", "Acero"],
        ["naut-08", "Oro rosa"],
        ["naut-05", "Negro PVD"],
      ]),
    },
    {
      id: "dial",
      label: "Esfera",
      question: "¿Qué esfera?",
      options: list("nautilus", [
        ["naut-01", "Amarillo a verde"],
        ["naut-02", "Azul"],
        ["naut-03", "Rosa"],
        ["naut-04", "Rosa a violeta"],
        ["naut-05", "Negra"],
        ["naut-06", "Gris plata"],
        ["naut-07", "Verde esmeralda"],
        ["naut-08", "Café degradado"],
        ["naut-09", "Blanca"],
        ["naut-10", "Gris carbón"],
        ["naut-11", "Azul Tiffany"],
        ["naut-12", "Negra · corazón abierto"],
        ["naut-13", "Azul · corazón abierto"],
        ["naut-14", "Turquesa · corazón abierto"],
        ["naut-15", "Azul marino · corazón abierto"],
        ["naut-16", "Negra y azul · corazón abierto"],
        ["naut-17", "Café chocolate"],
        ["naut-18", "Café · corazón abierto"],
        ["naut-19", "Negra · corazón abierto (oro rosa)"],
      ]),
    },
    {
      id: "strap",
      label: "Correa",
      question: "¿Y la correa?",
      options: list("nautilus", [
        ["naut-03", "Extensible acero"],
        ["naut-08", "Extensible oro rosa"],
        ["naut-05", "Extensible negro PVD"],
        ["naut-15", "Piel azul"],
        ["naut-16", "Piel negra"],
        ["naut-17", "Piel café"],
      ]),
    },
  ],
};

export const DEFAULT_PARTS: Record<ClassId, Build["parts"]> = {
  gmt: { case: "gmt-02", dial: "gmt-02", bezel: "gmt-02", bracelet: "gmt-02" },
  nautilus: { case: "naut-03", dial: "naut-02", strap: "naut-03" },
};

export const defaultBuild = (cls: ClassId): Build => ({ cls, parts: { ...DEFAULT_PARTS[cls] } });

export function optionOf(cls: ClassId, step: StepId, id: string) {
  return STEPS[cls].find((s) => s.id === step)!.options.find((o) => o.id === id)!;
}

export function encodeBuild(build: Build) {
  return [build.cls, ...STEPS[build.cls].map((s) => build.parts[s.id])].join(".");
}

export function decodeBuild(value: string | null): Build | null {
  if (!value) return null;
  const [cls, ...ids] = value.split(".");
  if (cls !== "gmt" && cls !== "nautilus") return null;
  const steps = STEPS[cls];
  if (ids.length !== steps.length) return null;
  const parts: Build["parts"] = {};
  for (const [i, step] of steps.entries()) {
    if (!step.options.some((o) => o.id === ids[i])) return null;
    parts[step.id] = ids[i];
  }
  return { cls, parts };
}

export type Layer = { slot: string; src: string };

const src = (cls: ClassId, name: string) => `/builder/leo/${cls}/${name}.webp`;

/** Capas de atrás hacia adelante, todas del mismo lienzo 1000 x 2000. */
export function layersOf(build: Build): Layer[] {
  const p = build.parts;
  if (build.cls === "gmt") {
    return [
      { slot: "bracelet", src: src("gmt", `bracelet-${p.bracelet}`) },
      { slot: "case", src: src("gmt", `case-${p.case}`) },
      { slot: "shadow", src: src("gmt", `shadowbezel-${p.case}`) },
      { slot: "dial", src: src("gmt", `dial-${p.dial}`) },
      { slot: "shadow", src: src("gmt", "shadowdial") },
      { slot: "bezel", src: src("gmt", `bezel-${p.bezel}`) },
    ];
  }
  return [
    { slot: "strap", src: src("nautilus", `strap-${p.strap}`) },
    { slot: "dial", src: src("nautilus", `dial-${p.dial}`) },
    { slot: "shadow", src: src("nautilus", "shadowdial") },
    { slot: "case", src: src("nautilus", `case-${p.case}`) },
  ];
}

/** Imagen de la pieza para el selector. */
export function thumbOf(cls: ClassId, step: StepId, id: string) {
  const type = step === "bracelet" ? "bracelet" : step;
  return src(cls, `${type}-${id}`);
}
