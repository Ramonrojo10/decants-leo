/**
 * Número de WhatsApp de Decants Leo en formato internacional, solo dígitos
 * (ej. "526641234567"). Mientras esté vacío, los enlaces abren WhatsApp sin
 * destinatario y el cliente elige el chat.
 */
export const WHATSAPP_NUMBER = "";

export const INSTAGRAM_URL = "https://www.instagram.com/decants.leo/";

export function whatsappLink(message: string) {
  const base = WHATSAPP_NUMBER ? `https://wa.me/${WHATSAPP_NUMBER}` : "https://wa.me/";
  return `${base}?text=${encodeURIComponent(message)}`;
}

export const GENERAL_MESSAGE =
  "Hola Decants Leo. Quiero conocer el stock disponible de relojes y accesorios.";
