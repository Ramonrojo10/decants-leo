/**
 * Número de WhatsApp de Decants Leo en formato internacional, solo dígitos
 * (ej. "526641234567"). Si se vacía, los enlaces abren WhatsApp sin destinatario.
 */
export const WHATSAPP_NUMBER = "526651426008";
export const WHATSAPP_DISPLAY = "+52 665 142 6008";
export const SITE_URL = "https://decantsleo.online";

export const INSTAGRAM_URL = "https://www.instagram.com/decants.leo/";

export function whatsappLink(message: string) {
  const base = WHATSAPP_NUMBER ? `https://wa.me/${WHATSAPP_NUMBER}` : "https://wa.me/";
  return `${base}?text=${encodeURIComponent(message)}`;
}

export const GENERAL_MESSAGE =
  "Hola Decants Leo. Quiero conocer el stock disponible de relojes y accesorios.";
