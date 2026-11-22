"use client";

/* eslint-disable @next/next/no-img-element */

import { useState } from "react";
import { coverOf, products, type Category } from "../data/products";
import { Check, Heart, Plus } from "./icons";
import { useStore } from "./store";

const filters: Array<"Todo" | Category> = ["Todo", "Seiko Mods", "Relojes", "Accesorios"];

export function Catalog() {
  const [filter, setFilter] = useState<(typeof filters)[number]>("Todo");
  const { favorites, inquiry, toggleFavorite, toggleInquiry, openDetail } = useStore();
  const visible = filter === "Todo" ? products : products.filter((p) => p.category === filter);

  return (
    <section className="stock" id="stock">
      <div className="stock-head">
        <h2>Stock seleccionado</h2>
        <p>
          Lo que está listo para entregarse en Tijuana. Precio, componentes y disponibilidad
          se confirman por mensaje antes de comprar.
        </p>
      </div>

      <div className="stock-bar">
        <div className="filters" role="group" aria-label="Filtrar por categoría">
          {filters.map((item) => (
            <button
              key={item}
              className={filter === item ? "is-active" : ""}
              aria-pressed={filter === item}
              onClick={() => setFilter(item)}
            >
              {item}
            </button>
          ))}
        </div>
        <span className="stock-count">{visible.length} {visible.length === 1 ? "pieza" : "piezas"}</span>
      </div>

      <ul className="grid">
        {visible.map((product) => {
          const cover = coverOf(product);
          const saved = favorites.includes(product.id);
          const added = inquiry.includes(product.id);
          return (
            <li key={product.id} className="card">
              <button className="card-media" onClick={() => openDetail(product)} aria-label={`Ver ${product.name}`}>
                <img
                  src={cover.src}
                  alt={product.name}
                  width={800}
                  height={1000}
                  loading="lazy"
                  style={{ objectPosition: cover.position }}
                  className={cover.kind === "studio" ? "is-studio" : ""}
                />
                <span className="card-view">Ver pieza</span>
              </button>
              <div className="card-body">
                <div>
                  <h3>{product.name}</h3>
                  <p className={`status ${product.immediate ? "status--live" : ""}`}>{product.label}</p>
                </div>
                <div className="card-actions">
                  <button
                    className={`icon-btn ${saved ? "is-on" : ""}`}
                    onClick={() => toggleFavorite(product.id)}
                    aria-pressed={saved}
                    aria-label={saved ? `Quitar ${product.name} de favoritos` : `Guardar ${product.name}`}
                  >
                    <Heart filled={saved} />
                  </button>
                  <button
                    className={`icon-btn ${added ? "is-on" : ""}`}
                    onClick={() => toggleInquiry(product.id)}
                    aria-pressed={added}
                    aria-label={added ? `Quitar ${product.name} de mi selección` : `Agregar ${product.name} a mi selección`}
                  >
                    {added ? <Check /> : <Plus />}
                  </button>
                </div>
              </div>
            </li>
          );
        })}
      </ul>
    </section>
  );
}
