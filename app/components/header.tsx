"use client";

import { useEffect, useRef, useState } from "react";
import { Bag, Close, Menu } from "./icons";
import { useStore } from "./store";

const links = [
  { href: "#stock", label: "Stock" },
  { href: "#arma", label: "Arma el tuyo" },
  { href: "#mods", label: "Seiko Mods" },
  { href: "#accesorios", label: "Accesorios" },
  { href: "#contacto", label: "Contacto" },
];

export function Wordmark({ className = "" }: { className?: string }) {
  return (
    <span className={`wordmark ${className}`}>
      <span>DECANTS</span>
      <b>LEO</b>
    </span>
  );
}

export function Header({ home = "" }: { home?: string }) {
  const { inquiry, openDrawer } = useStore();
  const [menuOpen, setMenuOpen] = useState(false);
  const [musicOn, setMusicOn] = useState(false);
  const [solid, setSolid] = useState(false);
  const audioRef = useRef<HTMLAudioElement>(null);

  useEffect(() => {
    const onScroll = () => setSolid(window.scrollY > 40);
    onScroll();
    window.addEventListener("scroll", onScroll, { passive: true });
    return () => window.removeEventListener("scroll", onScroll);
  }, []);

  useEffect(() => {
    const audio = audioRef.current;
    if (!audio) return;
    audio.volume = 0.18;
    if (musicOn) audio.play().catch(() => setMusicOn(false));
    else audio.pause();
  }, [musicOn]);

  useEffect(() => {
    const onVisibility = () => {
      const audio = audioRef.current;
      if (!audio) return;
      if (document.hidden) audio.pause();
      else if (musicOn) audio.play().catch(() => undefined);
    };
    document.addEventListener("visibilitychange", onVisibility);
    return () => document.removeEventListener("visibilitychange", onVisibility);
  }, [musicOn]);

  return (
    <header className={`site-header ${solid || menuOpen ? "is-solid" : ""}`}>
      <audio ref={audioRef} src="/audio/deep-techno-ambience.mp3" loop preload="none" />
      <a href={home ? "/" : "#inicio"} className="brand-link" aria-label="Decants Leo, inicio">
        <Wordmark />
      </a>

      <nav className={`nav ${menuOpen ? "is-open" : ""}`} aria-label="Principal">
        {links.map((link) => (
          <a key={link.href} href={home && link.href !== "#arma" ? `${home}${link.href}` : link.href} onClick={() => setMenuOpen(false)}>
            {link.label}
          </a>
        ))}
      </nav>

      <div className="header-tools">
        <button
          className={`tool sound ${musicOn ? "is-on" : ""}`}
          onClick={() => setMusicOn((value) => !value)}
          aria-pressed={musicOn}
          aria-label={musicOn ? "Pausar música" : "Reproducir música"}
        >
          <span className="sound-bars" aria-hidden="true"><i /><i /><i /><i /></span>
          <span className="sound-label">{musicOn ? "Música" : "Sonido"}</span>
        </button>
        <button
          className="tool"
          onClick={openDrawer}
          aria-label={`Abrir mi selección, ${inquiry.length} piezas`}
        >
          <Bag />
          {inquiry.length > 0 && <span className="tool-count">{inquiry.length}</span>}
        </button>
        <button
          className="tool menu-toggle"
          onClick={() => setMenuOpen((value) => !value)}
          aria-label={menuOpen ? "Cerrar menú" : "Abrir menú"}
          aria-expanded={menuOpen}
        >
          {menuOpen ? <Close /> : <Menu />}
        </button>
      </div>
    </header>
  );
}
