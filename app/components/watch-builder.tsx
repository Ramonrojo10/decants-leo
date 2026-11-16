"use client";

/* eslint-disable @next/next/no-img-element */

import { useEffect, useRef, useState } from "react";
import {
  DEFAULT_BUILD,
  DRAW_ORDER,
  FAMILY,
  decodeBuild,
  encodeBuild,
  isAllowed,
  layerSrc,
  normalize,
  optionOf,
  steps,
  type Build,
  type StepId,
} from "../data/builder";
import { whatsappLink } from "../lib/site";
import { ArrowUpRight, Check, WhatsApp } from "./icons";

const SUMMARY = steps.length;

type RenderState =
  | { status: "idle" }
  | { status: "loading" }
  | { status: "done"; imageUrl: string; key: string }
  | { status: "error"; message: string };

/** `fullStrap`: usa la capa con la correa completa (vista alejada). */
function layersOf(build: Build, fullStrap = false) {
  return DRAW_ORDER.flatMap((slot) =>
    slot.startsWith("light-")
      ? [{ slot, layer: slot, depth: DRAW_ORDER.indexOf(slot) }]
      : optionOf(slot as StepId, build[slot as StepId]).layers.map((layer) => ({
          slot,
          layer: slot === "strap" && fullStrap ? `${layer}-full` : layer,
          depth: DRAW_ORDER.indexOf(slot),
        })),
  );
}

/** Junta las capas reales en una sola imagen (lo que se manda al render). */
async function composeImage(build: Build) {
  const size = 1000;
  const canvas = document.createElement("canvas");
  canvas.width = canvas.height = size;
  const ctx = canvas.getContext("2d")!;
  ctx.fillStyle = "#0b0b0b";
  ctx.fillRect(0, 0, size, size);
  for (const { slot, layer } of layersOf(build)) {
    const img = new Image();
    img.src = layerSrc(layer);
    await img.decode();
    // las correas tienen el doble de alto, centradas en el mismo eje
    if (slot === "strap") ctx.drawImage(img, 0, -size / 2, size, size * 2);
    else ctx.drawImage(img, 0, 0, size, size);
  }
  return canvas.toDataURL("image/jpeg", 0.9);
}

export function WatchBuilder() {
  const stageRef = useRef<HTMLDivElement>(null);
  const watchRef = useRef<HTMLDivElement>(null);
  const [build, setBuild] = useState<Build>(DEFAULT_BUILD);
  const [active, setActive] = useState(0);
  const [assembled, setAssembled] = useState(false);
  const [lastChanged, setLastChanged] = useState<StepId | null>(null);
  const [copied, setCopied] = useState(false);
  const [render, setRender] = useState<RenderState>({ status: "idle" });

  // Restaura un armado compartido (?arma=…) y arma el reloj al verlo.
  useEffect(() => {
    const shared = decodeBuild(new URLSearchParams(window.location.search).get("arma"));
    if (shared) setBuild(shared);

    const stage = stageRef.current;
    if (!stage) return;
    const observer = new IntersectionObserver(
      ([entry]) => {
        if (entry.isIntersecting) {
          setAssembled(true);
          observer.disconnect();
        }
      },
      { threshold: 0.15 },
    );
    observer.observe(stage);
    return () => observer.disconnect();
  }, []);

  // Inclinación 3D sutil que sigue al puntero (solo con mouse).
  useEffect(() => {
    const stage = stageRef.current;
    const watch = watchRef.current;
    if (!stage || !watch || window.matchMedia("(prefers-reduced-motion: reduce)").matches) return;
    const onMove = (event: PointerEvent) => {
      if (event.pointerType !== "mouse") return;
      const rect = stage.getBoundingClientRect();
      const x = (event.clientX - rect.left) / rect.width - 0.5;
      const y = (event.clientY - rect.top) / rect.height - 0.5;
      watch.style.setProperty("--ry", `${x * 10}deg`);
      watch.style.setProperty("--rx", `${10 - y * 8}deg`);
    };
    const onLeave = () => {
      watch.style.removeProperty("--ry");
      watch.style.removeProperty("--rx");
    };
    stage.addEventListener("pointermove", onMove);
    stage.addEventListener("pointerleave", onLeave);
    return () => {
      stage.removeEventListener("pointermove", onMove);
      stage.removeEventListener("pointerleave", onLeave);
    };
  }, []);

  const choose = (step: StepId, id: string) => {
    setBuild((current) => normalize({ ...current, [step]: id }));
    setLastChanged(step);
  };

  const shareUrl = () => {
    const url = new URL(window.location.href);
    url.searchParams.set("arma", encodeBuild(build));
    url.hash = "arma";
    return url.toString();
  };

  const summaryLines = steps.map((s) => `${s.label}: ${optionOf(s.id, build[s.id]).name}`);
  const sendLink = () =>
    whatsappLink(
      `Hola Decants Leo. Quiero armar este Seiko Mod (${FAMILY.name}):\n${summaryLines.join(
        "\n",
      )}\n¿Me confirman disponibilidad y precio?\n${shareUrl()}`,
    );

  const copy = async () => {
    try {
      await navigator.clipboard.writeText(shareUrl());
      setCopied(true);
      setTimeout(() => setCopied(false), 1800);
    } catch {}
  };

  const requestRender = async () => {
    const key = encodeBuild(build);
    setRender({ status: "loading" });
    try {
      const image = await composeImage(build);
      const response = await fetch("/api/render", {
        method: "POST",
        headers: { "content-type": "application/json" },
        body: JSON.stringify({
          build: key,
          parts: steps.map((s) => {
            const option = optionOf(s.id, build[s.id]);
            return { step: s.label, name: option.name, detail: option.detail };
          }),
          image,
        }),
      });
      if (response.status === 404 || response.status === 501) {
        setRender({ status: "error", message: "La vista realista todavía no está conectada al servidor." });
        return;
      }
      const data = (await response.json().catch(() => null)) as { imageUrl?: string; error?: string } | null;
      if (!response.ok || !data?.imageUrl) {
        setRender({ status: "error", message: data?.error ?? "No se pudo generar la vista. Intenta de nuevo." });
        return;
      }
      setRender({ status: "done", imageUrl: data.imageUrl, key });
    } catch {
      setRender({ status: "error", message: "No se pudo generar la vista. Intenta de nuevo." });
    }
  };

  const step = steps[active];
  const strapView = step?.id === "strap";
  const renderIsCurrent = render.status === "done" && render.key === encodeBuild(build);

  return (
    <section className="builder" id="arma" aria-labelledby="arma-title">
      <div className="builder-head">
        <h2 id="arma-title">Arma tu Seiko Mod</h2>
        <p>
          Elige cada pieza y mira cómo queda. Leo lo arma a mano y te confirma componentes y
          precio antes de empezar.
        </p>
        <p className="builder-proto">Piezas reales de Namoki Mods · fotos del proveedor</p>
      </div>

      <div className="builder-body">
        <div
          ref={stageRef}
          className={`builder-stage ${assembled ? "is-assembled" : ""} ${strapView ? "is-strap-view" : ""}`}
        >
          <div className="builder-scene">
            <div ref={watchRef} className="builder-watch" role="img" aria-label={`Reloj armado: ${summaryLines.join(", ")}`}>
              {layersOf(build, strapView).map(({ slot, layer, depth }) => (
                <img
                  key={`${slot}-${layer}`}
                  src={layerSrc(layer)}
                  alt=""
                  draggable={false}
                  decoding="async"
                  className={[
                    "builder-layer",
                    `builder-layer--${slot}`,
                    layer.endsWith("-seconds") ? "is-seconds" : "",
                    layer.endsWith("-full") ? "is-full" : "",
                    lastChanged === slot ? "is-fresh" : "",
                  ].join(" ")}
                  style={{ "--depth": depth } as React.CSSProperties}
                />
              ))}
            </div>
          </div>
          <p className="builder-family">
            {FAMILY.name}
            <span>{FAMILY.note}</span>
          </p>
        </div>

        <div className="builder-panel">
          <ol className="builder-steps" aria-label="Pasos">
            {steps.map((s, i) => (
              <li key={s.id}>
                <button
                  className={i === active ? "is-active" : i < active ? "is-done" : ""}
                  onClick={() => setActive(i)}
                  aria-current={i === active ? "step" : undefined}
                >
                  <span>{i + 1}</span>
                  {s.label}
                </button>
              </li>
            ))}
            <li>
              <button
                className={active === SUMMARY ? "is-active" : ""}
                onClick={() => setActive(SUMMARY)}
                aria-current={active === SUMMARY ? "step" : undefined}
              >
                <span>
                  <Check size={14} />
                </span>
                Resumen
              </button>
            </li>
          </ol>

          {active < SUMMARY ? (
            <div className="builder-options" key={step.id}>
              <h3>{step.question}</h3>
              <div className="option-grid" role="radiogroup" aria-label={step.label}>
                {step.options.map((option) => {
                  const allowed = isAllowed(option, build);
                  const selected = build[step.id] === option.id;
                  return (
                    <button
                      key={option.id}
                      role="radio"
                      aria-checked={selected}
                      disabled={!allowed}
                      className={`option ${selected ? "is-selected" : ""}`}
                      onClick={() => choose(step.id, option.id)}
                    >
                      <span className={`option-thumb option-thumb--${step.id}`}>
                        <img src={layerSrc(option.thumb)} alt="" loading="lazy" decoding="async" />
                      </span>
                      <span className="option-text">
                        <b>{option.name}</b>
                        <small>{allowed ? option.detail : option.requiresNote ?? "No compatible con tu selección"}</small>
                      </span>
                      {selected && <Check size={16} className="option-check" />}
                    </button>
                  );
                })}
              </div>
              <div className="builder-nav">
                <button className="btn btn--line" onClick={() => setActive(Math.max(0, active - 1))} disabled={active === 0}>
                  Anterior
                </button>
                <button className="btn btn--solid" onClick={() => setActive(active + 1)}>
                  {active === SUMMARY - 1 ? "Ver resumen" : "Siguiente"}
                </button>
              </div>
            </div>
          ) : (
            <div className="builder-options builder-summary" key="summary">
              <h3>Tu reloj</h3>
              <dl className="spec-table">
                {steps.map((s) => (
                  <div key={s.id}>
                    <dt>{s.label}</dt>
                    <dd>
                      <button onClick={() => setActive(steps.indexOf(s))}>{optionOf(s.id, build[s.id]).name}</button>
                    </dd>
                  </div>
                ))}
                <div>
                  <dt>Movimiento</dt>
                  <dd>Seiko NH35 automático</dd>
                </div>
                <div>
                  <dt>Precio</dt>
                  <dd>Se confirma con Leo</dd>
                </div>
              </dl>

              <div className="builder-render">
                {renderIsCurrent && render.status === "done" ? (
                  <figure>
                    <img src={render.imageUrl} alt="Vista realista de tu reloj" />
                    <figcaption>Vista realista generada con IA a partir de tus piezas. Leo confirma el resultado final.</figcaption>
                  </figure>
                ) : (
                  <button className="btn btn--line" onClick={requestRender} disabled={render.status === "loading"}>
                    {render.status === "loading" ? "Generando tu reloj…" : "Ver mi reloj realista"}
                  </button>
                )}
                {render.status === "error" && <p className="builder-render-error">{render.message}</p>}
              </div>

              <div className="builder-nav">
                <a className="btn btn--solid" href={sendLink()} target="_blank" rel="noreferrer">
                  <WhatsApp /> Enviar a Leo
                </a>
                <button className="btn btn--line" onClick={copy}>
                  {copied ? "Enlace copiado" : "Copiar enlace"} {!copied && <ArrowUpRight />}
                </button>
              </div>
              <button
                className="builder-reset"
                onClick={() => {
                  setBuild(DEFAULT_BUILD);
                  setActive(0);
                  setLastChanged(null);
                  setRender({ status: "idle" });
                }}
              >
                Empezar de nuevo
              </button>
            </div>
          )}
        </div>
      </div>
    </section>
  );
}
