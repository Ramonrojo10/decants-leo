"use client";

/* eslint-disable @next/next/no-img-element */

import { useEffect, useMemo, useRef, useState } from "react";

type Category = "Todos" | "Seiko Mods" | "Relojes" | "Accesorios";

type Product = {
  id: string;
  name: string;
  category: Exclude<Category, "Todos">;
  label: string;
  image: string;
  position: string;
  note: string;
  reference: string;
};

const products: Product[] = [
  {
    id: "santos-dumont",
    name: "Santos Dumont",
    category: "Seiko Mods",
    label: "Entrega inmediata",
    image: "/products/santos-dumont-seiko-mod.png",
    position: "50% 50%",
    note: "Diseño rectangular, esfera clara y correa de piel negra.",
    reference: "Mod personalizado con movimiento Seiko",
  },
  {
    id: "gmt-bruce-wayne",
    name: "GMT Bruce Wayne",
    category: "Seiko Mods",
    label: "Entrega inmediata",
    image: "/products/gmt-bruce-wayne-seiko-mod.png",
    position: "50% 48%",
    note: "Bisel GMT bicolor y brazalete estilo jubilee.",
    reference: "Mod personalizado con movimiento Seiko",
  },
  {
    id: "santos-classic",
    name: "Santos Classic",
    category: "Seiko Mods",
    label: "Disponible",
    image: "/products/santos-seiko-mod.png",
    position: "50% 50%",
    note: "Acero, números romanos y una silueta limpia.",
    reference: "Mod personalizado con movimiento Seiko",
  },
  {
    id: "daytona-rainbow",
    name: "Daytona Rainbow",
    category: "Seiko Mods",
    label: "Pieza especial",
    image: "/products/daytona-rainbow-seiko-mod.png",
    position: "50% 48%",
    note: "Cronógrafo visual con bisel multicolor y acabado bicolor.",
    reference: "Mod personalizado con movimiento Seiko",
  },
  {
    id: "big-bang",
    name: "Big Bang",
    category: "Seiko Mods",
    label: "Entrega inmediata",
    image: "/products/hublot-big-bang-seiko-mod.png",
    position: "50% 47%",
    note: "Caja deportiva, correa de caucho y presencia contundente.",
    reference: "Mod personalizado con movimiento Seiko",
  },
  {
    id: "santos-full-ice",
    name: "Santos Full Ice",
    category: "Relojes",
    label: "Consultar disponibilidad",
    image: "/products/santos-full-ice.png",
    position: "50% 48%",
    note: "Acabado brillante y esfera negra de alto contraste.",
    reference: "Pieza de catálogo · especificaciones por confirmar",
  },
  {
    id: "ap-swatch-necklace",
    name: "Octagonal Necklace",
    category: "Accesorios",
    label: "Disponible",
    image: "/products/ap-swatch-necklace.png",
    position: "50% 48%",
    note: "Accesorio de cuello con caja octagonal y acabado monocromático.",
    reference: "Accesorio inspirado · marca independiente",
  },
];

const filters: Category[] = ["Todos", "Seiko Mods", "Relojes", "Accesorios"];

function Icon({
  children,
  label,
}: {
  children: React.ReactNode;
  label?: string;
}) {
  return (
    <span className="icon" aria-hidden={label ? undefined : true} aria-label={label}>
      {children}
    </span>
  );
}

export default function Home() {
  const [entered, setEntered] = useState(false);
  const [musicOn, setMusicOn] = useState(false);
  const [filter, setFilter] = useState<Category>("Todos");
  const [selected, setSelected] = useState<Product | null>(null);
  const [favorites, setFavorites] = useState<string[]>([]);
  const [inquiry, setInquiry] = useState<string[]>([]);
  const [drawerOpen, setDrawerOpen] = useState(false);
  const [menuOpen, setMenuOpen] = useState(false);
  const [scrolled, setScrolled] = useState(false);
  const audioRef = useRef<HTMLAudioElement>(null);

  const visibleProducts = useMemo(
    () =>
      filter === "Todos"
        ? products
        : products.filter((product) => product.category === filter),
    [filter],
  );

  useEffect(() => {
    const restoreStoredSelection = window.requestAnimationFrame(() => {
      try {
        setFavorites(JSON.parse(localStorage.getItem("dl-favorites") || "[]"));
        setInquiry(JSON.parse(localStorage.getItem("dl-inquiry") || "[]"));
      } catch {
        // A private browser session can deny storage; the experience still works.
      }
    });
    const onScroll = () => setScrolled(window.scrollY > 28);
    window.addEventListener("scroll", onScroll, { passive: true });
    return () => {
      window.cancelAnimationFrame(restoreStoredSelection);
      window.removeEventListener("scroll", onScroll);
    };
  }, []);

  useEffect(() => {
    try {
      localStorage.setItem("dl-favorites", JSON.stringify(favorites));
    } catch {}
  }, [favorites]);

  useEffect(() => {
    try {
      localStorage.setItem("dl-inquiry", JSON.stringify(inquiry));
    } catch {}
  }, [inquiry]);

  useEffect(() => {
    const audio = audioRef.current;
    if (!audio) return;
    audio.volume = 0.18;
    if (musicOn) {
      audio.play().catch(() => setMusicOn(false));
    } else {
      audio.pause();
    }
  }, [musicOn, entered]);

  useEffect(() => {
    const audio = audioRef.current;
    const handleVisibility = () => {
      if (!audio) return;
      if (document.hidden) audio.pause();
      else if (musicOn) audio.play().catch(() => undefined);
    };
    document.addEventListener("visibilitychange", handleVisibility);
    return () => document.removeEventListener("visibilitychange", handleVisibility);
  }, [musicOn]);

  useEffect(() => {
    document.body.style.overflow = selected || drawerOpen || !entered ? "hidden" : "";
    return () => {
      document.body.style.overflow = "";
    };
  }, [selected, drawerOpen, entered]);

  const enter = (withMusic: boolean) => {
    setEntered(true);
    setMusicOn(withMusic);
  };

  const toggleFavorite = (id: string) => {
    setFavorites((current) =>
      current.includes(id)
        ? current.filter((item) => item !== id)
        : [...current, id],
    );
  };

  const toggleInquiry = (id: string) => {
    setInquiry((current) =>
      current.includes(id)
        ? current.filter((item) => item !== id)
        : [...current, id],
    );
  };

  const inquiryProducts = products.filter((product) => inquiry.includes(product.id));
  const message = inquiryProducts.length
    ? `Hola Decants Leo. Me interesan estas piezas: ${inquiryProducts
        .map((product) => product.name)
        .join(", ")}. ¿Me comparten disponibilidad, especificaciones y precio?`
    : "Hola Decants Leo. Quiero conocer el stock disponible de relojes y accesorios.";
  const whatsappUrl = `https://wa.me/?text=${encodeURIComponent(message)}`;

  return (
    <main>
      <audio
        ref={audioRef}
        src="/audio/deep-techno-ambience.mp3"
        loop
        preload="none"
      />

      <div className={`entry-gate ${entered ? "entry-gate--hidden" : ""}`}>
        <div className="entry-orbit" aria-hidden="true">
          <span />
          <span />
          <span />
        </div>
        <div className="entry-copy">
          <div className="wordmark wordmark--entry">
            <span>DECANTS</span>
            <b>LEO</b>
          </div>
          <p className="eyebrow">Watches · Accessories · Tijuana</p>
          <h1>El tiempo,<br />a tu manera.</h1>
          <p className="entry-description">
            Una selección de relojes y accesorios con carácter.
          </p>
          <div className="entry-actions">
            <button className="button button--light" onClick={() => enter(true)}>
              <Icon>♪</Icon> Entrar con música
            </button>
            <button className="button button--ghost" onClick={() => enter(false)}>
              Entrar en silencio
            </button>
          </div>
          <small>La música inicia únicamente con tu permiso.</small>
        </div>
        <div className="entry-index" aria-hidden="true">DL / 01</div>
      </div>

      <header className={`site-header ${scrolled ? "site-header--scrolled" : ""}`}>
        <a href="#inicio" className="wordmark" aria-label="Decants Leo, inicio">
          <span>DECANTS</span>
          <b>LEO</b>
        </a>
        <nav className={`nav ${menuOpen ? "nav--open" : ""}`} aria-label="Principal">
          <a href="#catalogo" onClick={() => setMenuOpen(false)}>Stock</a>
          <a href="#mods" onClick={() => setMenuOpen(false)}>Seiko Mods</a>
          <a href="#universo" onClick={() => setMenuOpen(false)}>Universo Leo</a>
          <a href="#contacto" onClick={() => setMenuOpen(false)}>Contacto</a>
        </nav>
        <div className="header-actions">
          <button
            className={`icon-button sound-control ${musicOn ? "is-active" : ""}`}
            onClick={() => setMusicOn((value) => !value)}
            aria-label={musicOn ? "Pausar música" : "Reproducir música"}
          >
            <span className="sound-bars" aria-hidden="true"><i /><i /><i /></span>
          </button>
          <button
            className="icon-button inquiry-button"
            onClick={() => setDrawerOpen(true)}
            aria-label={`Abrir selección, ${inquiry.length} productos`}
          >
            <Icon>＋</Icon>
            {inquiry.length > 0 && <span className="count">{inquiry.length}</span>}
          </button>
          <button
            className="menu-button"
            onClick={() => setMenuOpen((value) => !value)}
            aria-label="Abrir menú"
            aria-expanded={menuOpen}
          >
            <span /><span />
          </button>
        </div>
      </header>

      <section className="hero" id="inicio">
        <div className="hero-media" aria-hidden="true">
          <img
            src="/products/santos-dumont-seiko-mod.png"
            alt=""
            style={{ objectPosition: "50% 48%" }}
          />
          <div className="hero-shade" />
        </div>
        <div className="hero-dial" aria-hidden="true" />
        <div className="hero-content">
          <p className="eyebrow">Selección 2026 · Baja California</p>
          <h2>Tu próximo reloj<br /><em>no pasa desapercibido.</em></h2>
          <p className="hero-description">
            Seiko Mods, piezas seleccionadas y accesorios para construir un estilo
            propio. Stock real, atención directa y entrega local.
          </p>
          <div className="hero-actions">
            <a href="#catalogo" className="button button--light">
              Ver stock <Icon>↘</Icon>
            </a>
            <a href={whatsappUrl} target="_blank" rel="noreferrer" className="text-link">
              Consultar por WhatsApp <span>→</span>
            </a>
          </div>
        </div>
        <div className="hero-meta">
          <span>01</span>
          <p>Disponibilidad<br />sujeta a confirmación</p>
        </div>
        <a href="#catalogo" className="scroll-cue" aria-label="Bajar al catálogo">
          <span>Scroll</span><i />
        </a>
      </section>

      <section className="marquee" aria-label="Servicios">
        <div>
          <span>ENTREGA LOCAL</span><i>✦</i>
          <span>ATENCIÓN DIRECTA</span><i>✦</i>
          <span>PIEZAS CON CARÁCTER</span><i>✦</i>
          <span>STOCK ACTUAL</span><i>✦</i>
          <span>ENTREGA LOCAL</span><i>✦</i>
          <span>ATENCIÓN DIRECTA</span><i>✦</i>
        </div>
      </section>

      <section className="catalog-section" id="catalogo">
        <div className="section-heading">
          <div>
            <p className="eyebrow">Entrega inmediata / Sobre pedido</p>
            <h2>Stock seleccionado</h2>
          </div>
          <p>
            Cada pieza se confirma directamente antes de la compra:
            disponibilidad, configuración y precio.
          </p>
        </div>

        <div className="catalog-toolbar">
          <div className="filters" aria-label="Filtrar productos">
            {filters.map((item) => (
              <button
                key={item}
                className={filter === item ? "is-active" : ""}
                onClick={() => setFilter(item)}
              >
                {item}
              </button>
            ))}
          </div>
          <span>{String(visibleProducts.length).padStart(2, "0")} piezas</span>
        </div>

        <div className="product-grid">
          {visibleProducts.map((product, index) => (
            <article className="product-card" key={product.id}>
              <button
                className="product-image"
                onClick={() => setSelected(product)}
                aria-label={`Ver detalles de ${product.name}`}
              >
                <img
                  src={product.image}
                  alt={product.name}
                  style={{ objectPosition: product.position }}
                />
                <span className="product-index">{String(index + 1).padStart(2, "0")}</span>
                <span className="quick-view">Ver pieza <Icon>↗</Icon></span>
              </button>
              <div className="product-info">
                <div>
                  <p>{product.category}</p>
                  <h3>{product.name}</h3>
                </div>
                <button
                  className={`favorite ${favorites.includes(product.id) ? "is-active" : ""}`}
                  onClick={() => toggleFavorite(product.id)}
                  aria-label={
                    favorites.includes(product.id)
                      ? `Quitar ${product.name} de favoritos`
                      : `Guardar ${product.name} en favoritos`
                  }
                >
                  {favorites.includes(product.id) ? "♥" : "♡"}
                </button>
              </div>
              <div className="availability"><i /> {product.label}</div>
            </article>
          ))}
        </div>
      </section>

      <section className="mods-section" id="mods">
        <div className="mods-visual">
          <img
            src="/products/gmt-bruce-wayne-seiko-mod.png"
            alt="GMT Bruce Wayne, ejemplo de Seiko Mod"
          />
          <div className="mods-ring" aria-hidden="true" />
          <span className="vertical-copy">CUSTOM / PERSONAL / DISTINCTIVE</span>
        </div>
        <div className="mods-copy">
          <p className="eyebrow">Seiko Mods</p>
          <h2>Una base confiable.<br />Una estética totalmente tuya.</h2>
          <p>
            Un Seiko Mod combina componentes seleccionados alrededor de un
            movimiento Seiko. El resultado es una pieza personalizada, creada
            para quienes buscan una silueta distinta sin perder la esencia
            mecánica.
          </p>
          <div className="spec-list">
            <div><span>01</span><p>Configuración visual personalizada</p></div>
            <div><span>02</span><p>Especificaciones confirmadas por pieza</p></div>
            <div><span>03</span><p>Atención antes y después de la entrega</p></div>
          </div>
          <a href={whatsappUrl} target="_blank" rel="noreferrer" className="button button--outline">
            Diseñar el mío <Icon>→</Icon>
          </a>
          <small>
            Los Seiko Mods son piezas personalizadas independientes. No existe
            afiliación con las marcas cuyos diseños puedan servir de inspiración.
          </small>
        </div>
      </section>

      <section className="universe-section" id="universo">
        <div className="universe-head">
          <p className="eyebrow">Más allá del reloj</p>
          <h2>Objetos que completan<br />tu lenguaje personal.</h2>
        </div>
        <div className="universe-grid">
          <button
            className="universe-card universe-card--large"
            onClick={() => setSelected(products[6])}
          >
            <img src="/products/ap-swatch-necklace.png" alt="Accesorio octagonal de cuello" />
            <span>Accesorios</span>
            <h3>Piezas para llevar distinto.</h3>
            <i>↗</i>
          </button>
          <div className="universe-card universe-card--type">
            <span>Próximamente</span>
            <h3>Tarjeteros</h3>
            <p>Diseños compactos para lo esencial.</p>
            <b>02</b>
          </div>
          <div className="universe-card universe-card--outline">
            <span>Próximamente</span>
            <h3>Pulseras</h3>
            <p>Detalles sutiles, presencia precisa.</p>
            <b>03</b>
          </div>
        </div>
      </section>

      <section className="trust-section">
        <div className="trust-number">1,891</div>
        <div className="trust-copy">
          <p className="eyebrow">Comunidad real</p>
          <h2>La confianza se construye<br />una entrega a la vez.</h2>
          <p>
            Desde Instagram hasta la entrega, hablamos contigo directamente.
            Pregunta, compara y confirma cada detalle antes de decidir.
          </p>
          <a
            href="https://www.instagram.com/decants.leo/"
            target="_blank"
            rel="noreferrer"
            className="text-link"
          >
            @decants.leo <span>↗</span>
          </a>
        </div>
        <div className="trust-image">
          <img src="/brand/instagram-profile.png" alt="Perfil de Instagram de Decants Leo" />
        </div>
      </section>

      <section className="contact-section" id="contacto">
        <div className="contact-dial" aria-hidden="true" />
        <p className="eyebrow">Tu próxima pieza empieza aquí</p>
        <h2>¿Cuál va contigo?</h2>
        <p>Cuéntanos qué buscas. Te compartimos opciones, stock y detalles reales.</p>
        <a href={whatsappUrl} target="_blank" rel="noreferrer" className="button button--light">
          Hablar con Leo <Icon>↗</Icon>
        </a>
      </section>

      <footer>
        <div className="wordmark wordmark--footer"><span>DECANTS</span><b>LEO</b></div>
        <div className="footer-links">
          <a href="#catalogo">Stock</a>
          <a href="#mods">Seiko Mods</a>
          <a href="https://www.instagram.com/decants.leo/" target="_blank" rel="noreferrer">Instagram</a>
          <a href={whatsappUrl} target="_blank" rel="noreferrer">WhatsApp</a>
        </div>
        <div className="footer-meta">
          <span>Tijuana · Baja California</span>
          <span>© {new Date().getFullYear()} Decants Leo</span>
        </div>
      </footer>

      {selected && (
        <div className="modal-shell" role="dialog" aria-modal="true" aria-label={selected.name}>
          <button className="modal-backdrop" onClick={() => setSelected(null)} aria-label="Cerrar" />
          <div className="product-modal">
            <button className="modal-close" onClick={() => setSelected(null)} aria-label="Cerrar detalle">×</button>
            <div className="modal-image">
              <img
                src={selected.image}
                alt={selected.name}
                style={{ objectPosition: selected.position }}
              />
            </div>
            <div className="modal-copy">
              <p className="eyebrow">{selected.category}</p>
              <h2>{selected.name}</h2>
              <div className="availability"><i /> {selected.label}</div>
              <p className="modal-description">{selected.note}</p>
              <dl>
                <div><dt>Referencia</dt><dd>{selected.reference}</dd></div>
                <div><dt>Precio</dt><dd>Disponible por mensaje</dd></div>
                <div><dt>Entrega</dt><dd>Se confirma al solicitar</dd></div>
              </dl>
              <button
                className={`button ${inquiry.includes(selected.id) ? "button--outline" : "button--light"}`}
                onClick={() => toggleInquiry(selected.id)}
              >
                {inquiry.includes(selected.id) ? "Quitar de selección" : "Agregar a mi selección"}
              </button>
              <a
                href={`https://wa.me/?text=${encodeURIComponent(
                  `Hola Decants Leo. Me interesa ${selected.name}. ¿Me comparten disponibilidad, especificaciones y precio?`,
                )}`}
                target="_blank"
                rel="noreferrer"
                className="text-link"
              >
                Consultar esta pieza <span>↗</span>
              </a>
              <small>
                Imágenes de referencia del inventario compartido. La configuración
                y autenticidad declarada se confirman antes de cualquier compra.
              </small>
            </div>
          </div>
        </div>
      )}

      <div className={`drawer-shell ${drawerOpen ? "drawer-shell--open" : ""}`} aria-hidden={!drawerOpen}>
        <button className="drawer-backdrop" onClick={() => setDrawerOpen(false)} aria-label="Cerrar selección" />
        <aside className="inquiry-drawer" aria-label="Mi selección">
          <div className="drawer-head">
            <div>
              <p className="eyebrow">Consulta personalizada</p>
              <h2>Mi selección</h2>
            </div>
            <button onClick={() => setDrawerOpen(false)} aria-label="Cerrar">×</button>
          </div>
          {inquiryProducts.length ? (
            <div className="drawer-products">
              {inquiryProducts.map((product) => (
                <div className="drawer-product" key={product.id}>
                  <img src={product.image} alt="" style={{ objectPosition: product.position }} />
                  <div><span>{product.category}</span><b>{product.name}</b></div>
                  <button onClick={() => toggleInquiry(product.id)} aria-label={`Quitar ${product.name}`}>×</button>
                </div>
              ))}
            </div>
          ) : (
            <div className="drawer-empty">
              <span>⌁</span>
              <h3>Aún no agregas piezas.</h3>
              <p>Abre un producto y agrégalo para preparar tu consulta.</p>
            </div>
          )}
          <div className="drawer-footer">
            <p>Te confirmaremos precio, especificaciones y disponibilidad.</p>
            <a href={whatsappUrl} target="_blank" rel="noreferrer" className="button button--light">
              Enviar consulta <Icon>↗</Icon>
            </a>
          </div>
        </aside>
      </div>
    </main>
  );
}
