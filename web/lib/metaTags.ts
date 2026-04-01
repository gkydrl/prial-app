import type { Metadata } from "next";
import { formatPrice } from "./formatPrice";

const SITE_NAME = "Prial";
const BASE_URL = "https://prial.io";
const CURRENT_YEAR = new Date().getFullYear();

const twitterCard = { card: "summary_large_image" as const };
const hreflang = { languages: { "tr-TR": BASE_URL } };

export function productMeta(product: {
  title: string;
  brand: string | null;
  stores: { current_price: number | null; in_stock: boolean }[];
  image_url: string | null;
}, slug: string): Metadata {
  const activeStores = product.stores.filter((s) => s.current_price && s.in_stock);
  const lowestPrice = activeStores.length
    ? Math.min(...activeStores.map((s) => s.current_price!))
    : null;
  const storeCount = activeStores.length;
  const brandText = product.brand ? `En Ucuz ${product.brand}` : "En Ucuz Fiyat";

  const title = `${product.title} Fiyatı ${CURRENT_YEAR} | ${brandText} | ${SITE_NAME}`;
  const description = lowestPrice
    ? `${product.title} en ucuz fiyatı ${formatPrice(lowestPrice)}. ${storeCount} mağazada karşılaştır. Fiyat geçmişi ve düşüş tahmini.`
    : `${product.title} fiyatlarını ${storeCount} mağazada karşılaştır.`;

  return {
    title,
    description,
    openGraph: {
      title,
      description,
      url: `${BASE_URL}/${slug}`,
      siteName: SITE_NAME,
      images: product.image_url ? [{ url: product.image_url, width: 800, height: 800 }] : [],
      type: "website",
      locale: "tr_TR",
    },
    twitter: {
      ...twitterCard,
      title,
      description,
      ...(product.image_url && { images: [product.image_url] }),
    },
    alternates: {
      canonical: `${BASE_URL}/${slug}`,
      ...hreflang,
    },
  };
}

export function categoryMeta(name: string, slug: string): Metadata {
  const title = `En Ucuz ${name} Fiyatları ${CURRENT_YEAR} | ${SITE_NAME}`;
  const description = `${name} kategorisindeki en ucuz fiyatları karşılaştır. Fiyat geçmişi, mağaza karşılaştırması ve fiyat düşüş bildirimi.`;

  return {
    title,
    description,
    openGraph: {
      title,
      description,
      url: `${BASE_URL}/${slug}`,
      siteName: SITE_NAME,
      type: "website",
      locale: "tr_TR",
    },
    twitter: { ...twitterCard, title, description },
    alternates: {
      canonical: `${BASE_URL}/${slug}`,
      ...hreflang,
    },
  };
}

export function brandMeta(brand: string, slug: string): Metadata {
  const title = `${brand} Fiyatları ${CURRENT_YEAR} - Tüm ${brand} Modelleri | ${SITE_NAME}`;
  const description = `${brand} ürünlerinin en ucuz fiyatlarını karşılaştır. Tüm ${brand} modelleri, fiyat geçmişi ve mağaza karşılaştırması.`;

  return {
    title,
    description,
    openGraph: {
      title,
      description,
      url: `${BASE_URL}/marka/${slug}`,
      siteName: SITE_NAME,
      type: "website",
      locale: "tr_TR",
    },
    twitter: { ...twitterCard, title, description },
    alternates: {
      canonical: `${BASE_URL}/marka/${slug}`,
      ...hreflang,
    },
  };
}

export function comparisonMeta(
  productA: { title: string },
  productB: { title: string },
  slug: string
): Metadata {
  const title = `${productA.title} vs ${productB.title} - Hangisi Daha Ucuz? | ${SITE_NAME}`;
  const description = `${productA.title} ve ${productB.title} fiyat karşılaştırması. Hangisi daha ucuz? Fiyat geçmişi ve detaylı karşılaştırma.`;

  return {
    title,
    description,
    openGraph: {
      title,
      description,
      url: `${BASE_URL}/karsilastir/${slug}`,
      siteName: SITE_NAME,
      type: "website",
      locale: "tr_TR",
    },
    twitter: { ...twitterCard, title, description },
    alternates: {
      canonical: `${BASE_URL}/karsilastir/${slug}`,
      ...hreflang,
    },
  };
}
