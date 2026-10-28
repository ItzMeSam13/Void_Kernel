import type { Metadata } from "next";
import { Manrope, Inter, IBM_Plex_Mono } from "next/font/google";
import "./globals.css";

/* ── Fonts (design 2.3) ──────────────────────────────── */

const manrope = Manrope({
  variable: "--font-manrope",
  subsets: ["latin"],
  weight: ["700", "800"],
  display: "swap",
});

const inter = Inter({
  variable: "--font-inter",
  subsets: ["latin"],
  weight: ["400", "500", "600"],
  display: "swap",
});

const ibmPlexMono = IBM_Plex_Mono({
  variable: "--font-ibm-plex-mono",
  subsets: ["latin"],
  weight: ["400", "500"],
  display: "swap",
});

/* ── Metadata ─────────────────────────────────────────── */

export const metadata: Metadata = {
  title: "Nith — Multimodal Misinformation Verification",
  description:
    "Verify claims with four independent analysis axes: claim veracity, media authenticity, cross-modal consistency, and historical reuse. Evidence signals, not verdicts.",
};

/* ── Root layout ──────────────────────────────────────── */

export default function RootLayout({ children }: LayoutProps<"/">) {
  return (
    <html
      lang="en"
      className={`${manrope.variable} ${inter.variable} ${ibmPlexMono.variable} h-full antialiased`}
    >
      <body className="min-h-full flex flex-col">{children}</body>
    </html>
  );
}
