import type { ProductResponse } from "@/lib/api";

const STORE_NAMES: Record<string, string> = {
  trendyol: "Trendyol",
  hepsiburada: "Hepsiburada",
  amazon: "Amazon Türkiye",
  n11: "n11.com",
  ciceksepeti: "Çiçek Sepeti",
  mediamarkt: "MediaMarkt",
  teknosa: "Teknosa",
  vatan: "Vatan Bilgisayar",
};

export function ProductSchema({ product }: { product: ProductResponse }) {
  const activeStores = product.stores.filter((s) => s.current_price && s.in_stock);
  const prices = activeStores.map((s) => s.current_price!);
  const lowPrice = prices.length ? Math.min(...prices) : undefined;
  const highPrice = prices.length ? Math.max(...prices) : undefined;

  const schema: Record<string, unknown> = {
    "@context": "https://schema.org",
    "@type": "Product",
    name: product.title,
    description: product.description || `${product.title} fiyat karşılaştırması`,
    ...(product.image_url && { image: product.image_url }),
    ...(product.brand && {
      brand: {
        "@type": "Brand",
        name: product.brand,
      },
    }),
  };

  if (lowPrice !== undefined && highPrice !== undefined) {
    const offers = activeStores.map((store) => ({
      "@type": "Offer",
      price: store.current_price!.toString(),
      priceCurrency: "TRY",
      availability: "https://schema.org/InStock",
      url: store.url,
      seller: {
        "@type": "Organization",
        name: STORE_NAMES[store.store] ?? store.store,
      },
    }));

    schema.offers = {
      "@type": "AggregateOffer",
      lowPrice: lowPrice.toString(),
      highPrice: highPrice.toString(),
      priceCurrency: "TRY",
      offerCount: activeStores.length,
      availability: "https://schema.org/InStock",
      offers,
    };
  }

  return (
    <script
      type="application/ld+json"
      dangerouslySetInnerHTML={{ __html: JSON.stringify(schema) }}
    />
  );
}
