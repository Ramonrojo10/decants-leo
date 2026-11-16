"use client";

/* eslint-disable @next/next/no-img-element */

import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useState,
} from "react";
import { coverOf, galleryOf, products, type Product } from "../data/products";
import { GENERAL_MESSAGE, whatsappLink } from "../lib/site";
import { ArrowUpRight, Close, WhatsApp } from "./icons";

type StoreState = {
  favorites: string[];
  inquiry: string[];
  toggleFavorite: (id: string) => void;
  toggleInquiry: (id: string) => void;
  openDetail: (product: Product) => void;
  openDrawer: () => void;
  inquiryLink: string;
};

const StoreContext = createContext<StoreState | null>(null);

function Gallery({ product }: { product: Product }) {
  const images = galleryOf(product);
  const [index, setIndex] = useState(0);
  const current = images[index];

  return (
    <div className="sheet-media">
      <figure className={`gallery-main ${current.kind === "studio" ? "is-studio" : ""}`}>
        <img src={current.src} alt={current.alt} style={{ objectPosition: current.position }} />
        <figcaption>{current.caption}</figcaption>
      </figure>
      {images.length > 1 && (
        <div className="gallery-thumbs" role="tablist" aria-label="Vistas de la pieza">
          {images.map((image, i) => (
            <button
              key={image.src}
              role="tab"
              aria-selected={i === index}
              aria-label={image.caption}
              className={i === index ? "is-active" : ""}
              onClick={() => setIndex(i)}
            >
              <img src={image.src} alt="" style={{ objectPosition: image.position }} />
            </button>
          ))}
        </div>
      )}
    </div>
  );
}

export function useStore() {
  const value = useContext(StoreContext);
  if (!value) throw new Error("useStore must be used inside <StoreProvider>");
  return value;
}

function usePersistentList(key: string) {
  const [list, setList] = useState<string[]>([]);
  const [ready, setReady] = useState(false);

  useEffect(() => {
    const frame = requestAnimationFrame(() => {
      try {
        const stored = JSON.parse(localStorage.getItem(key) || "[]");
        if (Array.isArray(stored)) setList(stored.filter((id) => typeof id === "string"));
      } catch {
        // Storage can be blocked in private sessions; the page still works.
      }
      setReady(true);
    });
    return () => cancelAnimationFrame(frame);
  }, [key]);

  useEffect(() => {
    if (!ready) return;
    try {
      localStorage.setItem(key, JSON.stringify(list));
    } catch {}
  }, [key, list, ready]);

  const toggle = useCallback(
    (id: string) =>
      setList((current) =>
        current.includes(id) ? current.filter((item) => item !== id) : [...current, id],
      ),
    [],
  );

  return [list, toggle] as const;
}

export function StoreProvider({ children }: { children: React.ReactNode }) {
  const [favorites, toggleFavorite] = usePersistentList("dl-favorites");
  const [inquiry, toggleInquiry] = usePersistentList("dl-inquiry");
  const [detail, setDetail] = useState<Product | null>(null);
  const [drawerOpen, setDrawerOpen] = useState(false);

  const inquiryProducts = products.filter((product) => inquiry.includes(product.id));
  const inquiryLink = whatsappLink(
    inquiryProducts.length
      ? `Hola Decants Leo. Me interesan estas piezas: ${inquiryProducts
          .map((product) => product.name)
          .join(", ")}. ¿Me comparten disponibilidad, especificaciones y precio?`
      : GENERAL_MESSAGE,
  );

  const sheetOpen = Boolean(detail) || drawerOpen;

  useEffect(() => {
    document.documentElement.classList.toggle("is-locked", sheetOpen);
    if (!sheetOpen) return;
    const onKey = (event: KeyboardEvent) => {
      if (event.key === "Escape") {
        setDetail(null);
        setDrawerOpen(false);
      }
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [sheetOpen]);

  const value = useMemo<StoreState>(
    () => ({
      favorites,
      inquiry,
      toggleFavorite,
      toggleInquiry,
      openDetail: (product) => {
        setDrawerOpen(false);
        setDetail(product);
      },
      openDrawer: () => {
        setDetail(null);
        setDrawerOpen(true);
      },
      inquiryLink,
    }),
    [favorites, inquiry, toggleFavorite, toggleInquiry, inquiryLink],
  );

  return (
    <StoreContext.Provider value={value}>
      {children}

      <div className={`sheet-shell ${sheetOpen ? "is-open" : ""}`} aria-hidden={!sheetOpen}>
        <button
          className="sheet-backdrop"
          tabIndex={-1}
          aria-label="Cerrar"
          onClick={() => {
            setDetail(null);
            setDrawerOpen(false);
          }}
        />

        {detail && (
          <aside className="sheet sheet--detail" role="dialog" aria-modal="true" aria-label={detail.name}>
            <button className="sheet-close" onClick={() => setDetail(null)} aria-label="Cerrar detalle">
              <Close />
            </button>
            <Gallery key={detail.id} product={detail} />
            <div className="sheet-body">
              <p className="sheet-category">{detail.category}</p>
              <h2>{detail.name}</h2>
              <p className={`status ${detail.immediate ? "status--live" : ""}`}>{detail.label}</p>
              <p className="sheet-note">{detail.note}</p>
              <dl className="spec-table">
                <div><dt>Referencia</dt><dd>{detail.reference}</dd></div>
                <div><dt>Precio</dt><dd>Por mensaje</dd></div>
                <div><dt>Entrega</dt><dd>Se confirma al solicitar</dd></div>
              </dl>
              <div className="sheet-actions">
                <button
                  className={`btn ${inquiry.includes(detail.id) ? "btn--quiet" : "btn--solid"}`}
                  onClick={() => toggleInquiry(detail.id)}
                >
                  {inquiry.includes(detail.id) ? "Quitar de mi selección" : "Agregar a mi selección"}
                </button>
                <a
                  className="btn btn--line"
                  href={whatsappLink(
                    `Hola Decants Leo. Me interesa ${detail.name}. ¿Me comparten disponibilidad, especificaciones y precio?`,
                  )}
                  target="_blank"
                  rel="noreferrer"
                >
                  <WhatsApp /> Preguntar por esta pieza
                </a>
              </div>
              <p className="fine-print">
                Fotos reales del inventario. La configuración y los componentes se confirman
                antes de cualquier compra.
              </p>
            </div>
          </aside>
        )}

        {drawerOpen && (
          <aside className="sheet sheet--drawer" role="dialog" aria-modal="true" aria-label="Mi selección">
            <header className="drawer-head">
              <h2>Mi selección</h2>
              <button className="sheet-close" onClick={() => setDrawerOpen(false)} aria-label="Cerrar selección">
                <Close />
              </button>
            </header>
            {inquiryProducts.length ? (
              <ul className="drawer-list">
                {inquiryProducts.map((product) => (
                  <li key={product.id}>
                    <img src={coverOf(product).src} alt="" style={{ objectPosition: coverOf(product).position }} />
                    <div>
                      <span>{product.category}</span>
                      <b>{product.name}</b>
                    </div>
                    <button onClick={() => toggleInquiry(product.id)} aria-label={`Quitar ${product.name}`}>
                      <Close size={16} />
                    </button>
                  </li>
                ))}
              </ul>
            ) : (
              <div className="drawer-empty">
                <h3>Todavía no eliges piezas.</h3>
                <p>Abre cualquier reloj del stock y agrégalo. Mandamos tu lista completa por WhatsApp en un solo mensaje.</p>
              </div>
            )}
            <footer className="drawer-foot">
              <p>Te respondemos con precio, componentes y disponibilidad de cada pieza.</p>
              <a className="btn btn--solid" href={inquiryLink} target="_blank" rel="noreferrer">
                Enviar por WhatsApp <ArrowUpRight />
              </a>
            </footer>
          </aside>
        )}
      </div>
    </StoreContext.Provider>
  );
}
