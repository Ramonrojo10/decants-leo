"use client";

/* eslint-disable @next/next/no-img-element */

import { useEffect, useRef, useState } from "react";
import {
  CLASSES,
  DEFAULT_PARTS,
  FAMILY,
  STEPS,
  decodeBuild,
  defaultBuild,
  encodeBuild,
  layersOf,
  optionOf,
  thumbOf,
  type Build,
  type ClassId,
  type StepId,
} from "../data/builder";
import { whatsappLink } from "../lib/site";
import { ArrowUpRight, Check, WhatsApp } from "./icons";

type RenderState =
  | { status: "idle" }
  | { status: "loading" }
  | { status: "done"; imageUrl: string; key: string }
  | { status: "error"; message: string };

/** Junta las capas reales en una sola imagen (recorte de 1000 x 1000 centrado en la esfera). */
async function composeImage(build: Build) {
  const size = 1000;
  const canvas = document.createElement("canvas");
  canvas.width = canvas.height = size;
  const ctx = canvas.getContext("2d")!;
  ctx.fillStyle = "#0b0b0b";
  ctx.fillRect(0, 0, size, size);
  for (const { src } of layersOf(build)) {
    const img = new Image();
    img.src = src;
    await img.decode();
    // el lienzo mide 1000 x 2000 y la esfera está en el centro
    ctx.drawImage(img, 0, -size / 2, size, size * 2);
  }
  return canvas.toDataURL("image/jpeg", 0.9);
}

export function WatchBuilder() {
  const stageRef = useRef<HTMLDivElement>(null);
  const watchRef = useRef<HTMLDivElement>(null);
  const [build, setBuild] = useState<Build>(() => defaultBuild("gmt"));
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

  const steps = STEPS[build.cls];
  const SUMMARY = steps.length;
  const className = CLASSES.find((c) => c.id === build.cls)!.name;

  const choose = (step: StepId, id: string) => {
    setBuild((current) => ({ ...current, parts: { ...current.parts, [step]: id } }));
    setLastChanged(step);
  };

  const chooseClass = (cls: ClassId) => {
    if (cls === build.cls) return;
    setBuild(defaultBuild(cls));
    setActive(0);
    setLastChanged(null);
    setRender({ status: "idle" });
  };

  const shareUrl = () => {
    const url = new URL(window.location.href);
    url.searchParams.set("arma", encodeBuild(build));
    url.hash = "arma";
    return url.toString();
  };

  const summaryLines = steps.map((s) => `${s.label}: ${optionOf(build.cls, s.id, build.parts[s.id]!).name}`);
  const sendLink = () =>
    whatsappLink(
      `Hola Decants Leo. Quiero armar este Seiko Mod (${className}):\n${summaryLines.join(
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
          parts: [
            { step: "Clase", name: className, detail: "Piezas de Leo" },
            ...steps.map((s) => {
              const option = optionOf(build.cls, s.id, build.parts[s.id]!);
              return { step: s.label, name: option.name, detail: option.detail };
            }),
          ],
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
  const layers = layersOf(build);
  const renderIsCurrent = render.status === "done" && render.key === encodeBuild(build);

  return (
    <section className="builder" id="arma" aria-labelledby="arma-title">
      <div className="builder-head">
        <h2 id="arma-title">Arma tu Seiko Mod</h2>
        <p>
          Elige cada pieza y mira cómo queda. Leo lo arma a mano y te confirma componentes y
          precio antes de empezar.
        </p>
        <p className="builder-proto">{FAMILY.note}</p>
      </div>

      <div className="builder-class" role="radiogroup" aria-label="Clase de reloj">
        {CLASSES.map((c) => (
          <button
            key={c.id}
            role="radio"
            aria-checked={build.cls === c.id}
            className={build.cls === c.id ? "is-active" : ""}
            onClick={() => chooseClass(c.id)}
          >
            {c.label}
          </button>
        ))}
      </div>

      <div className="builder-body">
        <div
          ref={stageRef}
          className={`builder-stage ${assembled ? "is-assembled" : ""}`}
        >
          <div className="builder-scene">
            <div ref={watchRef} className="builder-watch" role="img" aria-label={`Reloj armado: ${summaryLines.join(", ")}`}>
              {layers.map(({ slot, src }, depth) => (
                <img
                  key={`${build.cls}-${depth}-${src}`}
                  src={src}
                  alt=""
                  draggable={false}
                  decoding="async"
                  className={`builder-layer builder-layer--${slot} ${lastChanged === slot ? "is-fresh" : ""}`}
                  style={{ "--depth": depth } as React.CSSProperties}
                />
              ))}
            </div>
          </div>
          <p className="builder-family">
            {className} · {FAMILY.name}
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
                  const selected = build.parts[step.id] === option.id;
                  return (
                    <button
                      key={option.id}
                      role="radio"
                      aria-checked={selected}
                      className={`option ${selected ? "is-selected" : ""}`}
                      onClick={() => choose(step.id, option.id)}
                    >
                      <span className={`option-thumb option-thumb--${step.id}`}>
                        {step.id === "case" && (
                          <img src={thumbOf(build.cls, "dial", DEFAULT_PARTS[build.cls].dial!)} alt="" loading="lazy" decoding="async" />
                        )}
                        <img src={thumbOf(build.cls, step.id, option.id)} alt="" loading="lazy" decoding="async" />
                      </span>
                      <span className="option-text">
                        <b>{option.name}</b>
                        <small>{option.detail}</small>
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
                <div>
                  <dt>Clase</dt>
                  <dd>
                    <button onClick={() => setActive(0)}>{className}</button>
                  </dd>
                </div>
                {steps.map((s) => (
                  <div key={s.id}>
                    <dt>{s.label}</dt>
                    <dd>
                      <button onClick={() => setActive(steps.indexOf(s))}>{optionOf(build.cls, s.id, build.parts[s.id]!).name}</button>
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
                  setBuild(defaultBuild(build.cls));
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
