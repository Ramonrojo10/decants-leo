"use client";

/* eslint-disable @next/next/no-img-element */

import { coverOf, products } from "../data/products";
import { ArrowUpRight } from "./icons";
import { useStore } from "./store";

export function ShowcaseButton({ productId }: { productId: string }) {
  const { openDetail } = useStore();
  const product = products.find((item) => item.id === productId);
  if (!product) return null;
  const cover = coverOf(product);

  return (
    <button className="extra-feature" onClick={() => openDetail(product)}>
      <img src={cover.src} alt={product.name} loading="lazy" style={{ objectPosition: cover.position }} />
      <span className="extra-caption">
        <b>{product.name}</b>
        <span>{product.category} · {product.label}</span>
      </span>
      <ArrowUpRight className="extra-arrow" />
    </button>
  );
}
