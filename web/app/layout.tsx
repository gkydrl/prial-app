import type { Metadata } from "next";
import { Inter } from "next/font/google";
import "./globals.css";
import Header from "@/components/layout/Header";
import Footer from "@/components/layout/Footer";
import { WebSiteSchema } from "@/components/seo/WebSiteSchema";
import { OrganizationSchema } from "@/components/seo/OrganizationSchema";
import { StickyMobileCTA } from "@/components/layout/StickyMobileCTA";

const inter = Inter({
  subsets: ["latin", "latin-ext"],
  display: "swap",
});


export const metadata: Metadata = {
  title: {
    default: "Prial - Akıllı Alışveriş Asistanı | Fiyat Karşılaştırma & Takip",
    template: "%s | Prial",
  },
  description:
    "Binlerce üründe fiyat karşılaştırması, fiyat geçmişi ve düşüş bildirimi. Trendyol, Hepsiburada, Amazon ve daha fazlasında en ucuz fiyatı bul.",
  metadataBase: new URL("https://www.prial.io"),
  openGraph: {
    type: "website",
    locale: "tr_TR",
    siteName: "Prial",
  },
  twitter: {
    card: "summary_large_image",
  },
  alternates: {
    languages: {
      "tr-TR": "https://www.prial.io",
    },
  },
  robots: {
    index: true,
    follow: true,
  },
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="tr" className={inter.className}>
      <head>
        <link rel="preconnect" href="https://prial-app-production.up.railway.app" />
        <link rel="dns-prefetch" href="https://cdn.dsmcdn.com" />
        <link rel="dns-prefetch" href="https://productimages.hepsiburada.net" />
      </head>
      <body className="min-h-screen flex flex-col bg-white text-gray-900">
        <WebSiteSchema />
        <OrganizationSchema />
        <Header />
        <main className="flex-1">{children}</main>
        <Footer />
        <StickyMobileCTA />
      </body>
    </html>
  );
}
