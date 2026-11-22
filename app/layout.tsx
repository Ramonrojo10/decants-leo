import type { Metadata, Viewport } from "next";
import { Bodoni_Moda, Geist, Geist_Mono } from "next/font/google";
import "./globals.css";
import { INSTAGRAM_URL, SITE_URL, WHATSAPP_DISPLAY } from "./lib/site";

const geist = Geist({
  variable: "--font-geist",
  subsets: ["latin"],
});

const geistMono = Geist_Mono({
  variable: "--font-mono",
  subsets: ["latin"],
  preload: false,
});

const editorial = Bodoni_Moda({
  variable: "--font-editorial",
  subsets: ["latin"],
  weight: ["400", "500"],
  style: ["normal", "italic"],
  display: "swap",
  preload: false,
});

const DESCRIPTION =
  "Seiko Mods en Tijuana: arma tu reloj GMT, estilo Nautilus o estilo Santos pieza por pieza. Movimiento NH35, entrega en persona.";

export const viewport: Viewport = {
  themeColor: "#050505",
  colorScheme: "dark",
};

export const metadata: Metadata = {
  metadataBase: new URL(SITE_URL),
  title: {
    default: "Decants Leo · Seiko Mods en Tijuana | Arma tu reloj",
    template: "%s · Decants Leo",
  },
  description: DESCRIPTION,
  alternates: { canonical: "/" },
  openGraph: {
    title: "Decants Leo · Seiko Mods en Tijuana",
    description: DESCRIPTION,
    url: "/",
    siteName: "Decants Leo",
    type: "website",
    locale: "es_MX",
    images: [
      {
        url: "/og.jpg",
        width: 1200,
        height: 630,
        alt: "Decants Leo: Seiko Mods, relojes y accesorios en Tijuana",
      },
    ],
  },
  twitter: {
    card: "summary_large_image",
    title: "Decants Leo · Seiko Mods en Tijuana",
    description: DESCRIPTION,
    images: [
      {
        url: "/og.jpg",
        alt: "Decants Leo: Seiko Mods, relojes y accesorios en Tijuana",
      },
    ],
  },
};

const jsonLd = {
  "@context": "https://schema.org",
  "@graph": [
    {
      "@type": "WebSite",
      "@id": `${SITE_URL}/#website`,
      url: `${SITE_URL}/`,
      name: "Decants Leo",
      inLanguage: "es-MX",
      publisher: { "@id": `${SITE_URL}/#business` },
    },
    {
      "@type": ["Organization", "Store"],
      "@id": `${SITE_URL}/#business`,
      name: "Decants Leo",
      url: `${SITE_URL}/`,
      logo: `${SITE_URL}/icon.png`,
      image: `${SITE_URL}/og.jpg`,
      description: DESCRIPTION,
      telephone: WHATSAPP_DISPLAY,
      sameAs: [INSTAGRAM_URL],
      address: {
        "@type": "PostalAddress",
        addressLocality: "Tijuana",
        addressRegion: "Baja California",
        addressCountry: "MX",
      },
      areaServed: { "@type": "City", name: "Tijuana" },
    },
  ],
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="es">
      <body className={`${geist.variable} ${geistMono.variable} ${editorial.variable}`}>
        <script
          type="application/ld+json"
          dangerouslySetInnerHTML={{ __html: JSON.stringify(jsonLd).replace(/</g, "\\u003c") }}
        />
        {children}
      </body>
    </html>
  );
}
