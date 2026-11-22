import { Wordmark } from "./header";
import { INSTAGRAM_URL, WHATSAPP_DISPLAY, whatsappLink, GENERAL_MESSAGE } from "../lib/site";

export function SiteFooter({ home = "" }: { home?: string }) {
  return (
    <footer className="footer">
      <Wordmark />
      <nav aria-label="Pie de página">
        <a href={`${home}#stock`}>Stock</a>
        <a href={`${home}#mods`}>Seiko Mods</a>
        <a href="/gmt">Seiko Mod GMT</a>
        <a href="/nautilus">Estilo Nautilus</a>
        <a href="/santos">Estilo Santos</a>
        <a href={INSTAGRAM_URL} target="_blank" rel="noreferrer">Instagram</a>
        <a href={whatsappLink(GENERAL_MESSAGE)} target="_blank" rel="noreferrer">WhatsApp</a>
      </nav>
      <p>
        <a href={whatsappLink(GENERAL_MESSAGE)} target="_blank" rel="noreferrer">{WHATSAPP_DISPLAY}</a>
        {" · "}Entrega en persona en Tijuana
      </p>
      <p>Tijuana · Baja California · © {new Date().getFullYear()} Decants Leo</p>
    </footer>
  );
}
