/* eslint-disable @next/next/no-img-element */

import { ScrollVideo } from "./components/scroll-video";
import { Catalog } from "./components/catalog";
import { WatchBuilder } from "./components/watch-builder";
import { Header } from "./components/header";
import { ArrowUpRight, Instagram, WhatsApp } from "./components/icons";
import { ShowcaseButton } from "./components/showcase-button";
import { SiteFooter } from "./components/site-footer";
import { StoreProvider } from "./components/store";
import { GENERAL_MESSAGE, INSTAGRAM_URL, whatsappLink } from "./lib/site";

const modSteps = [
  {
    title: "Eliges la silueta",
    text: "Parte de una pieza del stock o de una referencia que te guste: caja, bisel y brazalete.",
  },
  {
    title: "Definimos los componentes",
    text: "Esfera, manecillas y cristal. Te confirmamos cada componente antes de armar.",
  },
  {
    title: "Se arma y se entrega",
    text: "Montado sobre movimiento Seiko automático y entregado en mano en Tijuana.",
  },
];

export default function Home() {
  return (
    <StoreProvider>
      <Header />
      <main>
        <ScrollVideo />

        <Catalog />

        <WatchBuilder />

        <p className="style-links">
          Páginas por estilo: <a href="/gmt">Seiko Mod GMT</a> · <a href="/nautilus">Estilo Nautilus</a> ·{" "}
          <a href="/santos">Estilo Santos</a>
        </p>

        <section className="mods" id="mods">
          <div className="mods-figure">
            <img src="/products/gmt-bruce-wayne-seiko-mod.jpg" alt="GMT Bruce Wayne en mano, foto real" loading="lazy" />
          </div>
          <div className="mods-text">
            <h2>Seiko Mods:<br /><em>una base confiable, una estética tuya.</em></h2>
            <p>
              Un Seiko Mod reúne componentes seleccionados alrededor de un movimiento Seiko. Es una
              pieza personalizada para quien quiere una silueta distinta sin perder lo mecánico.
            </p>
            <ol className="steps">
              {modSteps.map((step) => (
                <li key={step.title}>
                  <h3>{step.title}</h3>
                  <p>{step.text}</p>
                </li>
              ))}
            </ol>
            <a href="#arma" className="btn btn--solid">
              Arma el tuyo <ArrowUpRight />
            </a>
            <p className="fine-print">
              Los Seiko Mods son piezas personalizadas independientes. No hay afiliación con Seiko
              ni con las marcas cuyos diseños sirven de inspiración.
            </p>
          </div>
        </section>

        <section className="extras" id="accesorios">
          <div className="extras-head">
            <h2>Más allá del reloj</h2>
            <p>Objetos pequeños que completan lo que ya llevas en la muñeca.</p>
          </div>
          <div className="extras-row">
            <ShowcaseButton productId="octagonal-necklace" />
            <div className="extra-soon">
              <h3>Tarjeteros</h3>
              <p>Diseños compactos para lo esencial.</p>
              <span>Próximamente</span>
            </div>
            <div className="extra-soon">
              <h3>Pulseras</h3>
              <p>Detalles sutiles, presencia precisa.</p>
              <span>Próximamente</span>
            </div>
          </div>
        </section>

        <section className="community">
          <img src="/brand/instagram-profile.jpg" alt="Perfil de Instagram de Decants Leo" loading="lazy" />
          <div>
            <h2>Cada entrega, en historias.</h2>
            <p>
              El stock se publica primero en Instagram. Desde ahí hasta la entrega hablas
              directamente con Leo: preguntas, comparas y confirmas cada detalle.
            </p>
            <a href={INSTAGRAM_URL} target="_blank" rel="noreferrer" className="btn btn--line">
              <Instagram /> @decants.leo
            </a>
          </div>
        </section>

        <section className="closing" id="contacto">
          <h2>¿Cuál va contigo?</h2>
          <p>Cuéntanos qué buscas. Te mandamos opciones, stock y detalles reales.</p>
          <a href={whatsappLink(GENERAL_MESSAGE)} target="_blank" rel="noreferrer" className="btn btn--solid btn--large">
            <WhatsApp /> Hablar con Leo
          </a>
        </section>
      </main>

      <SiteFooter />
    </StoreProvider>
  );
}
