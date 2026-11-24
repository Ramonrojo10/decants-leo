import { Header } from "./header";
import { SiteFooter } from "./site-footer";
import { StoreProvider } from "./store";
import { WatchBuilder } from "./watch-builder";
import { ArrowUpRight, WhatsApp } from "./icons";
import { STEPS, type ClassId } from "../data/builder";
import { SITE_URL, whatsappLink } from "../lib/site";
import { withSharedBuild } from "../lib/share-meta";

export const STYLE_PAGES: Record<
  ClassId,
  { slug: ClassId; h1: string; short: string; title: string; description: string; crumb: string; waMessage: string; intro: string }
> = {
  gmt: {
    slug: "gmt",
    h1: "Seiko Mod GMT en Tijuana",
    short: "Seiko Mod GMT",
    crumb: "GMT",
    title: "Seiko Mod GMT en Tijuana",
    description:
      "Arma tu Seiko Mod GMT en Tijuana pieza por pieza: caja, esfera, bisel y extensible. Movimiento NH35, armado a mano por Leo y entrega en persona.",
    waMessage: "Hola Decants Leo. Quiero armar un Seiko Mod GMT. ¿Me ayudan a elegir las piezas?",
    intro: "En esta clase eliges caja, esfera, bisel y extensible.",
  },
  nautilus: {
    slug: "nautilus",
    h1: "Seiko Mod estilo Nautilus en Tijuana",
    short: "Estilo Nautilus",
    crumb: "Estilo Nautilus",
    title: "Seiko Mod estilo Nautilus en Tijuana",
    description:
      "Arma tu Seiko Mod estilo Nautilus en Tijuana pieza por pieza: caja, esfera y correa. Movimiento NH35, armado a mano por Leo y entrega en persona.",
    waMessage: "Hola Decants Leo. Quiero armar un Seiko Mod estilo Nautilus. ¿Me ayudan a elegir las piezas?",
    intro: "En esta clase eliges caja, esfera y correa o extensible.",
  },
  santos: {
    slug: "santos",
    h1: "Seiko Mod estilo Santos en Tijuana",
    short: "Estilo Santos",
    crumb: "Estilo Santos",
    title: "Seiko Mod estilo Santos en Tijuana",
    description:
      "Arma tu Seiko Mod estilo Santos en Tijuana pieza por pieza: caja, esfera y correa. Movimiento NH35, armado a mano por Leo y entrega en persona.",
    waMessage: "Hola Decants Leo. Quiero armar un Seiko Mod estilo Santos. ¿Me ayudan a elegir las piezas?",
    intro: "En esta clase eliges caja, esfera y correa o extensible.",
  },
  daytona: {
    slug: "daytona",
    h1: "Seiko Mod estilo Daytona en Tijuana",
    short: "Estilo Daytona",
    crumb: "Estilo Daytona",
    title: "Seiko Mod estilo Daytona en Tijuana",
    description:
      "Arma tu Seiko Mod estilo Daytona en Tijuana: caja con bisel, esfera y extensible. Movimiento NH35, armado a mano por Leo y entrega en persona.",
    waMessage: "Hola Decants Leo. Quiero armar un Seiko Mod estilo Daytona. ¿Me ayudan a elegir las piezas?",
    intro: "En esta clase eliges caja con bisel, esfera y extensible.",
  },
};

const GROUP_TITLES: Record<string, string> = {
  case: "Cajas",
  dial: "Esferas",
  bezel: "Biseles",
  bracelet: "Extensibles",
  strap: "Extensibles y correas",
};

export function metadataFor(cls: ClassId) {
  const page = STYLE_PAGES[cls];
  const url = `/${page.slug}`;
  const image = { url: "/og.jpg", width: 1200, height: 630, alt: "Decants Leo: Seiko Mods, relojes y accesorios en Tijuana" };
  return {
    title: page.title,
    description: page.description,
    alternates: { canonical: url },
    openGraph: {
      title: `${page.title} · Decants Leo`,
      description: page.description,
      url,
      siteName: "Decants Leo",
      type: "website" as const,
      locale: "es_MX",
      images: [image],
    },
    twitter: {
      card: "summary_large_image" as const,
      title: `${page.title} · Decants Leo`,
      description: page.description,
      images: [{ url: "/og.jpg", alt: image.alt }],
    },
  };
}

export async function generateStyleMetadata(cls: ClassId, searchParams: Promise<{ arma?: string | string[] }>) {
  return withSharedBuild(metadataFor(cls), (await searchParams).arma);
}

export function StyleLanding({ cls }: { cls: ClassId }) {
  const page = STYLE_PAGES[cls];
  const steps = STEPS[cls];
  const combos = steps.reduce((total, s) => total * s.options.length, 1);
  const comboText = combos.toLocaleString("es-MX");
  const others = (Object.keys(STYLE_PAGES) as ClassId[]).filter((id) => id !== cls);
  const styleName = cls === "gmt" ? "GMT" : `estilo ${page.crumb.replace("Estilo ", "")}`;

  const faqs = [
    {
      q: "¿Qué movimiento usa?",
      a: "Todos los Seiko Mod de Leo usan movimiento automático NH35.",
    },
    {
      q: "¿Puedo combinar cualquier pieza?",
      a: `Sí. Todas las piezas de la clase ${page.crumb.replace("Estilo ", "")} son combinables entre sí: hay ${comboText} combinaciones posibles.`,
    },
    {
      q: "¿Cómo pido el mío?",
      a: "Arma tu reloj en el armador de esta página y envía tu selección por WhatsApp. Leo confirma componentes y precio antes de empezar a armarlo.",
    },
    {
      q: "¿Dónde se entrega?",
      a: "Leo arma cada reloj a mano en Tijuana y la entrega es en persona en Tijuana.",
    },
  ];

  const jsonLd = {
    "@context": "https://schema.org",
    "@graph": [
      {
        "@type": "FAQPage",
        mainEntity: faqs.map((f) => ({
          "@type": "Question",
          name: f.q,
          acceptedAnswer: { "@type": "Answer", text: f.a },
        })),
      },
      {
        "@type": "BreadcrumbList",
        itemListElement: [
          { "@type": "ListItem", position: 1, name: "Inicio", item: `${SITE_URL}/` },
          { "@type": "ListItem", position: 2, name: page.crumb, item: `${SITE_URL}/${page.slug}` },
        ],
      },
    ],
  };

  return (
    <StoreProvider>
      <Header home="/" />
      <main>
        <script
          type="application/ld+json"
          dangerouslySetInnerHTML={{ __html: JSON.stringify(jsonLd).replace(/</g, "\\u003c") }}
        />
        <section className="style-hero">
          <nav className="style-crumbs" aria-label="Ruta">
            <a href="/">Inicio</a> › <span>{page.crumb}</span>
          </nav>
          <h1>{page.h1}</h1>
          <p>
            Leo arma cada reloj a mano en Tijuana, sobre movimiento automático NH35. Es un Seiko
            Mod {styleName}: una pieza personalizada, inspirada en ese estilo, sin afiliación con la
            marca que lo inspira.
          </p>
          <p>
            Todas las piezas de la clase son combinables. {page.intro} Leo confirma componentes y
            precio por WhatsApp antes de empezar, y la entrega es en persona en Tijuana.
          </p>
        </section>

        <WatchBuilder initialClass={cls} />

        <section className="style-options" aria-labelledby="opciones-title">
          <h2 id="opciones-title">Piezas disponibles · {page.crumb}</h2>
          <p>
            Hay {comboText} combinaciones posibles en esta clase. Estas son las opciones del armador.
          </p>
          <div className="style-options-grid">
            {steps.map((s) => (
              <div key={s.id}>
                <h3>{GROUP_TITLES[s.id] ?? s.label}</h3>
                <ul>
                  {s.options.map((o) => (
                    <li key={o.id}>{o.name}</li>
                  ))}
                </ul>
              </div>
            ))}
          </div>
        </section>

        <section className="style-faq" aria-labelledby="faq-title">
          <h2 id="faq-title">Preguntas frecuentes</h2>
          {faqs.map((f) => (
            <div key={f.q} className="style-faq-item">
              <h3>{f.q}</h3>
              <p>{f.a}</p>
            </div>
          ))}
        </section>

        <section className="closing">
          <h2>¿Listo para armarlo?</h2>
          <p>Cuéntale a Leo qué piezas quieres. Te confirma componentes y precio antes de empezar.</p>
          <a href={whatsappLink(page.waMessage)} target="_blank" rel="noreferrer" className="btn btn--solid btn--large">
            <WhatsApp /> Hablar con Leo
          </a>
          <p className="style-others">
            También armamos:{" "}
            {others.map((id, i) => (
              <span key={id}>
                {i > 0 && " · "}
                <a href={`/${id}`}>
                  {STYLE_PAGES[id].short} <ArrowUpRight />
                </a>
              </span>
            ))}
          </p>
        </section>
      </main>
      <SiteFooter home="/" />
    </StoreProvider>
  );
}
