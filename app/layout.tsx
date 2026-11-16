import type { Metadata } from "next";
import { Bodoni_Moda, Geist, Geist_Mono } from "next/font/google";
import "./globals.css";

const geist = Geist({
  variable: "--font-geist",
  subsets: ["latin"],
});

const geistMono = Geist_Mono({
  variable: "--font-mono",
  subsets: ["latin"],
});

const editorial = Bodoni_Moda({
  variable: "--font-editorial",
  subsets: ["latin"],
  weight: ["400", "500"],
  style: ["normal", "italic"],
});

export const metadata: Metadata = {
  metadataBase: new URL("https://decantsleo.karmaops.online"),
  title: {
    default: "Decants Leo — Relojes y accesorios",
    template: "%s · Decants Leo",
  },
  description:
    "Seiko Mods, relojes y accesorios seleccionados en Tijuana. Stock actual, atención directa y piezas con carácter.",
  keywords: [
    "Decants Leo",
    "relojes Tijuana",
    "Seiko Mods",
    "relojes personalizados",
    "accesorios",
  ],
  openGraph: {
    title: "Decants Leo — El tiempo, a tu manera.",
    description:
      "Relojes y accesorios seleccionados. Stock actual y atención directa en Tijuana.",
    type: "website",
    locale: "es_MX",
    images: ["/og.png"],
  },
  twitter: {
    card: "summary_large_image",
    title: "Decants Leo — El tiempo, a tu manera.",
    description: "Relojes y accesorios seleccionados en Tijuana.",
    images: ["/og.png"],
  },
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="es">
      <body className={`${geist.variable} ${geistMono.variable} ${editorial.variable}`}>
        {children}
      </body>
    </html>
  );
}
