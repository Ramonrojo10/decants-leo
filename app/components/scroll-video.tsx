"use client";

import { useEffect, useRef, useState } from "react";
import { GENERAL_MESSAGE, whatsappLink } from "../lib/site";
import { ArrowDown, WhatsApp } from "./icons";

/**
 * Video de portada controlado por el scroll.
 *
 * El video (generado en Higgsfield) se convierte a una secuencia de cuadros
 * con `scripts/video-to-frames.sh`, que escribe /public/hero/frames/NNNN.jpg y
 * /public/hero/manifest.json ({ "frames": N, "width": W, "height": H }).
 * Mientras no exista el manifest, la portada muestra solo el texto.
 */

type Manifest = { frames: number; width: number; height: number };

const frameSrc = (index: number) => `/hero/frames/${String(index + 1).padStart(4, "0")}.jpg`;
const clamp = (v: number) => Math.min(1, Math.max(0, v));

export function ScrollVideo() {
  const sectionRef = useRef<HTMLElement>(null);
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const [manifest, setManifest] = useState<Manifest | null>(null);
  const [phase, setPhase] = useState<"intro" | "play" | "done">("intro");

  useEffect(() => {
    let cancelled = false;
    fetch("/hero/manifest.json")
      .then((response) => (response.ok ? response.json() : null))
      .then((data: Manifest | null) => {
        if (!cancelled && data?.frames) setManifest(data);
      })
      .catch(() => undefined);
    return () => {
      cancelled = true;
    };
  }, []);

  useEffect(() => {
    const section = sectionRef.current;
    const canvas = canvasRef.current;
    if (!section || !canvas || !manifest) return;
    const context = canvas.getContext("2d");
    if (!context) return;

    canvas.width = manifest.width;
    canvas.height = manifest.height;

    const images: HTMLImageElement[] = [];
    let current = -1;
    let frame = 0;
    let lastPhase = "";
    const reduce = window.matchMedia("(prefers-reduced-motion: reduce)");

    const draw = (index: number) => {
      // fall back to the nearest frame that has already loaded
      for (let i = index; i >= 0; i--) {
        const image = images[i];
        if (image?.complete && image.naturalWidth) {
          context.drawImage(image, 0, 0, canvas.width, canvas.height);
          return;
        }
      }
    };

    const update = () => {
      frame = 0;
      const rect = section.getBoundingClientRect();
      const distance = rect.height - window.innerHeight;
      const progress = reduce.matches ? 1 : distance > 0 ? clamp(-rect.top / distance) : 1;
      const index = Math.round(progress * (manifest.frames - 1));
      if (index !== current) {
        current = index;
        draw(index);
      }
      const next = progress < 0.06 ? "intro" : progress < 0.94 ? "play" : "done";
      if (next !== lastPhase) {
        lastPhase = next;
        setPhase(next);
      }
    };
    const schedule = () => {
      if (!frame) frame = requestAnimationFrame(update);
    };

    // Progressive loading: first (and last) frame now, the rest in small
    // batches when the browser is idle or the user starts scrolling.
    const load = (i: number) => {
      if (images[i]) return;
      const image = new Image();
      image.decoding = "async";
      image.onload = () => {
        current = -1;
        schedule();
      };
      image.src = frameSrc(i);
      images[i] = image;
    };
    // Order: coarse stride first so scrubbing has nearby frames early, then fill gaps.
    const order: number[] = [];
    const seen = new Set<number>();
    for (const stride of [16, 8, 4, 2, 1]) {
      for (let i = 0; i < manifest.frames; i += stride) {
        if (!seen.has(i)) {
          seen.add(i);
          order.push(i);
        }
      }
    }
    if (!seen.has(manifest.frames - 1)) order.push(manifest.frames - 1);
    load(0);

    let cursor = 1;
    let stopped = false;
    let timer = 0;
    const idle = (cb: () => void) => {
      const w = window as Window & { requestIdleCallback?: (cb: () => void) => number };
      if (w.requestIdleCallback) w.requestIdleCallback(cb);
      else timer = window.setTimeout(cb, 120);
    };
    const pump = () => {
      if (stopped) return;
      for (let n = 0; n < 6 && cursor < order.length; n++) load(order[cursor++]);
      if (cursor < order.length) idle(pump);
    };
    const kick = () => {
      window.removeEventListener("scroll", kick);
      pump();
    };
    window.addEventListener("scroll", kick, { passive: true, once: true });
    idle(pump);

    schedule();
    window.addEventListener("scroll", schedule, { passive: true });
    window.addEventListener("resize", schedule);
    return () => {
      stopped = true;
      clearTimeout(timer);
      window.removeEventListener("scroll", kick);
      cancelAnimationFrame(frame);
      window.removeEventListener("scroll", schedule);
      window.removeEventListener("resize", schedule);
    };
  }, [manifest]);

  return (
    <section
      ref={sectionRef}
      id="inicio"
      className={`scroll-video ${manifest ? "has-video" : ""}`}
      data-phase={phase}
    >
      <div className="scroll-video-stage">
        {manifest && <canvas ref={canvasRef} className="scroll-video-canvas" aria-hidden="true" />}
        <div className="scroll-video-shade" aria-hidden="true" />

        <div className="hero-copy hero-copy--intro">
          <p className="place">Seiko Mods · Tijuana, Baja California</p>
          <h1>El tiempo,<br />a tu manera.</h1>
          <p className="lede">Seiko Mods, relojes seleccionados y accesorios con carácter.</p>
          {manifest ? (
            <p className="scroll-hint"><ArrowDown size={16} /> Desliza</p>
          ) : (
            <div className="cta-row">
              <a href="#stock" className="btn btn--solid">Ver stock</a>
              <a href={whatsappLink(GENERAL_MESSAGE)} target="_blank" rel="noreferrer" className="btn btn--line">
                <WhatsApp /> Escríbenos
              </a>
            </div>
          )}
        </div>

        {manifest && (
          <div className="hero-copy hero-copy--done">
            <h2>Tu próximo reloj<br /><em>no pasa desapercibido.</em></h2>
            <div className="cta-row">
              <a href="#stock" className="btn btn--solid">Ver stock</a>
              <a href={whatsappLink(GENERAL_MESSAGE)} target="_blank" rel="noreferrer" className="btn btn--line">
                <WhatsApp /> Escríbenos
              </a>
            </div>
          </div>
        )}
      </div>
    </section>
  );
}
