import { notFound } from "next/navigation";
import type { Metadata } from "next";
import { getProduct, getProductPriceHistory, getCategoryProducts, filterDisplayable, normalizeProduct } from "@/lib/api";
import { extractShortId, productSlug } from "@/lib/slugify";
import { productMeta } from "@/lib/metaTags";
import { formatPrice } from "@/lib/formatPrice";
import { Breadcrumb } from "@/components/layout/Breadcrumb";
import { ProductSchema } from "@/components/seo/ProductSchema";
import dynamic from "next/dynamic";

const PriceHistoryChart = dynamic(
  () => import("@/components/product/PriceHistoryChart").then((m) => m.PriceHistoryChart),
  { loading: () => <div className="h-[400px] bg-gray-50 rounded-xl animate-pulse" /> }
);
import { VariantSelector } from "@/components/product/VariantSelector";
import { AppDownloadCTA } from "@/components/product/AppDownloadCTA";
import { ProductImage } from "@/components/product/ProductImage";
import { PrialSays } from "@/components/product/PrialSays";
import { FAQSchema } from "@/components/seo/FAQSchema";
import { ProductCard } from "@/components/product/ProductCard";

interface Props {
  params: Promise<{ categorySlug: string; productSlug: string }>;
}

async function findProduct(slug: string) {
  const shortId = extractShortId(slug);
  const API_BASE =
    process.env.NEXT_PUBLIC_API_BASE_URL ??
    "https://prial-app-production.up.railway.app/api/v1";

  // Try short ID endpoint first
  try {
    const res = await fetch(`${API_BASE}/products/by-id-short/${shortId}`, {
      next: { revalidate: 900, tags: [`product-short-${shortId}`] },
    });
    if (res.ok) {
      const product = await res.json();
      return normalizeProduct(product);
    }
  } catch {
    // fallback below
  }

  // Fallback: search products matching shortId prefix
  try {
    const res = await fetch(`${API_BASE}/products?limit=200`, {
      next: { revalidate: 900 },
    });
    if (res.ok) {
      const products = await res.json();
      const match = products.find((p: { id: string }) =>
        p.id.replace(/-/g, "").startsWith(shortId)
      );
      if (match) return normalizeProduct(match);
    }
  } catch {
    // fallback failed
  }

  return null;
}

export async function generateMetadata({ params }: Props): Promise<Metadata> {
  const { categorySlug, productSlug: pSlug } = await params;
  const product = await findProduct(pSlug);
  if (!product) return {};

  const slug = `${categorySlug}/${productSlug(product.title, product.id)}`;
  return productMeta(product, slug);
}

export const revalidate = 900; // 15 minutes

export default async function ProductDetailPage({ params }: Props) {
  const { categorySlug, productSlug: pSlug } = await params;

  const product = await findProduct(pSlug);
  if (!product) notFound();

  // Image, fiyat veya AI recommendation yoksa yayınlama
  const hasPrice = product.stores?.some(
    (s: { current_price: number | null; in_stock: boolean }) =>
      s.current_price != null && s.in_stock
  );
  if (!product.image_url || !hasPrice || !product.recommendation) notFound();

  const [priceHistory, rawRelated] = await Promise.all([
    getProductPriceHistory(product.id).catch(() => []),
    getCategoryProducts(categorySlug, 1, 10, "alarm_count", 3600).catch(() => []),
  ]);

  const relatedProducts = filterDisplayable(rawRelated)
    .filter((p) => p.id !== product.id)
    .slice(0, 5);

  const activeStores = product.stores
    .filter(
      (s: { current_price: number | null; in_stock: boolean }) =>
        s.current_price != null && s.in_stock
    )
    .sort(
      (a: { current_price: number | null }, b: { current_price: number | null }) =>
        (a.current_price ?? Infinity) - (b.current_price ?? Infinity)
    );

  const bestStore = activeStores[0] ?? null;
  const secondBestStore = activeStores[1] ?? null;
  const bestPrice = bestStore?.current_price ?? null;
  const highestPrice = activeStores.length
    ? Math.max(...activeStores.map((s: { current_price: number | null }) => s.current_price!))
    : null;

  // Get category name from slug
  const categoryName = categorySlug
    .split("-")
    .map((w: string) => w.charAt(0).toUpperCase() + w.slice(1))
    .join(" ");

  return (
    <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-6">
      <ProductSchema product={product} />

      <Breadcrumb
        items={[
          { name: categoryName, href: `/${categorySlug}` },
          {
            name: product.short_title || product.title,
            href: `/${categorySlug}/${productSlug(product.title, product.id)}`,
          },
        ]}
      />

      {/* Product Header: Image + PrialSays */}
      <div className="mt-6 grid grid-cols-1 lg:grid-cols-2 gap-8">
        {/* Image */}
        <div className="relative bg-white rounded-2xl p-8 border border-gray-100 aspect-square">
          <ProductImage
            src={product.image_url}
            alt={`${product.brand ? product.brand + " " : ""}${product.title} - fiyat karşılaştırma`}
            fill
            className="object-contain p-8"
            sizes="(max-width: 1024px) 100vw, 50vw"
            priority
          />
        </div>

        {/* AI Prediction + Product Info */}
        <div>
          {product.brand && (
            <a
              href={`/marka/${product.brand.toLowerCase()}`}
              className="text-sm text-brand hover:underline"
            >
              {product.brand}
            </a>
          )}
          <h1 className="text-2xl md:text-3xl font-bold text-gray-900 mt-1">
            {product.title}
          </h1>

          {/* PrialSays — Hero element */}
          <div className="mt-5">
            <PrialSays product={product} bestStore={bestStore} secondBestStore={secondBestStore} />
          </div>

          {/* Variants */}
          {product.variants && product.variants.length > 1 && (
            <div className="mt-6">
              <VariantSelector
                variants={product.variants}
                stores={product.stores}
                categorySlug={categorySlug}
              />
            </div>
          )}
        </div>
      </div>

      {/* Price Summary */}
      {(() => {
        // Sanity check: l1y fiyatlar mevcut fiyatın %30'undan düşükse gösterme (hatalı veri)
        const saneL1yLowest = product.l1y_lowest_price && bestPrice
          && product.l1y_lowest_price >= bestPrice * 0.3
          ? product.l1y_lowest_price : null;
        const saneL1yHighest = product.l1y_highest_price && bestPrice
          && product.l1y_highest_price >= bestPrice * 0.3
          ? product.l1y_highest_price : null;
        const saneLowestEver = product.lowest_price_ever && bestPrice
          && product.lowest_price_ever >= bestPrice * 0.1
          ? product.lowest_price_ever : null;

        return (
          <section className="mt-8">
            <div className="p-5 bg-surface rounded-xl border border-gray-100">
              <div className="flex flex-wrap items-end gap-6">
                <div>
                  <p className="text-sm text-gray-500">En Ucuz Fiyat</p>
                  <p className="text-3xl font-bold text-brand">
                    {formatPrice(bestPrice)}
                  </p>
                </div>
                {highestPrice && highestPrice > (bestPrice ?? 0) && (
                  <div>
                    <p className="text-sm text-gray-500">En Yüksek</p>
                    <p className="text-lg text-gray-400">
                      {formatPrice(highestPrice)}
                    </p>
                  </div>
                )}
                {saneL1yLowest && (
                  <div>
                    <p className="text-sm text-gray-500">Son 1 Yıl En Düşük</p>
                    <p className="text-lg font-semibold text-success">
                      {formatPrice(saneL1yLowest)}
                    </p>
                  </div>
                )}
                {saneL1yHighest && saneL1yHighest > (bestPrice ?? 0) && (
                  <div>
                    <p className="text-sm text-gray-500">Son 1 Yıl En Yüksek</p>
                    <p className="text-lg text-gray-400">
                      {formatPrice(saneL1yHighest)}
                    </p>
                  </div>
                )}
                {saneLowestEver && (
                  <div>
                    <p className="text-sm text-gray-500">Tüm Zamanların En Düşüğü</p>
                    <p className="text-lg font-semibold text-success">
                      {formatPrice(saneLowestEver)}
                    </p>
                  </div>
                )}
              </div>
            </div>
          </section>
        );
      })()}

      {/* Price History Chart */}
      {priceHistory.length > 1 && (
        <section className="mt-10">
          <h2 className="text-2xl font-bold text-gray-900 mb-4">
            Fiyat Geçmişi
          </h2>
          <PriceHistoryChart data={priceHistory} />
        </section>
      )}

      {/* Description */}
      {product.description && (
        <section className="mt-10">
          <h2 className="text-2xl font-bold text-gray-900 mb-4">
            Ürün Açıklaması
          </h2>
          <p className="text-gray-600 leading-relaxed whitespace-pre-line">
            {product.description}
          </p>
        </section>
      )}

      {/* FAQ Section */}
      <FAQSchema
        title={product.title}
        stores={product.stores}
        predicted_direction={product.predicted_direction}
        recommendation={product.recommendation}
        reasoningText={product.reasoning_text}
        l1yLowestPrice={product.l1y_lowest_price}
        bestPrice={bestPrice}
        brand={product.brand}
        categoryName={categoryName}
      />

      {/* Related Products */}
      {relatedProducts.length > 0 && (
        <section className="mt-10">
          <h2 className="text-2xl font-bold text-gray-900 mb-4">
            Benzer Ürünler
          </h2>
          <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-4 xl:grid-cols-5 gap-4">
            {relatedProducts.map((rp) => {
              const shortA = product.id.replace(/-/g, "").slice(0, 8);
              const shortB = rp.id.replace(/-/g, "").slice(0, 8);
              return (
                <div key={rp.id} className="flex flex-col">
                  <ProductCard product={rp} categorySlug={categorySlug} />
                  <a
                    href={`/karsilastir/${shortA}-vs-${shortB}`}
                    className="mt-1.5 text-center text-xs text-brand hover:underline font-medium"
                  >
                    Karşılaştır
                  </a>
                </div>
              );
            })}
          </div>
        </section>
      )}

      {/* App Download CTA */}
      <section className="mt-10">
        <AppDownloadCTA productId={product.id} />
      </section>
    </div>
  );
}
