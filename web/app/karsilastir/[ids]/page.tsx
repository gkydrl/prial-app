import { notFound } from "next/navigation";
import type { Metadata } from "next";
import { getProduct, getProductPriceHistory } from "@/lib/api";
import { comparisonMeta } from "@/lib/metaTags";
import { Breadcrumb } from "@/components/layout/Breadcrumb";
import { ProductImage } from "@/components/product/ProductImage";
import dynamic from "next/dynamic";

const PriceHistoryChart = dynamic(
  () => import("@/components/product/PriceHistoryChart").then((m) => m.PriceHistoryChart),
  { loading: () => <div className="h-[400px] bg-gray-50 rounded-xl animate-pulse" /> }
);
import { formatPrice } from "@/lib/formatPrice";

interface Props {
  params: Promise<{ ids: string }>;
}

function parseIds(idsParam: string): { idA: string; idB: string; slug: string } | null {
  // Format: {idA}-vs-{idB} or {idA}-vs-{idB}/{slug}
  const vsMatch = idsParam.match(/^([a-f0-9-]+)-vs-([a-f0-9-]+)/);
  if (!vsMatch) return null;
  return { idA: vsMatch[1], idB: vsMatch[2], slug: idsParam };
}

export async function generateMetadata({ params }: Props): Promise<Metadata> {
  const { ids } = await params;
  const parsed = parseIds(ids);
  if (!parsed) return {};

  try {
    const [productA, productB] = await Promise.all([
      getProduct(parsed.idA),
      getProduct(parsed.idB),
    ]);
    return comparisonMeta(productA, productB, parsed.slug);
  } catch {
    return {};
  }
}

export const revalidate = 900;

export default async function ComparisonPage({ params }: Props) {
  const { ids } = await params;
  const parsed = parseIds(ids);
  if (!parsed) notFound();

  let productA, productB;
  try {
    [productA, productB] = await Promise.all([
      getProduct(parsed.idA),
      getProduct(parsed.idB),
    ]);
  } catch {
    notFound();
  }

  const [historyA, historyB] = await Promise.all([
    getProductPriceHistory(productA.id).catch(() => []),
    getProductPriceHistory(productB.id).catch(() => []),
  ]);

  const getBestPrice = (stores: { current_price: number | null; in_stock: boolean }[]) => {
    const active = stores.filter((s) => s.current_price && s.in_stock);
    return active.length ? Math.min(...active.map((s) => s.current_price!)) : null;
  };

  const priceA = getBestPrice(productA.stores);
  const priceB = getBestPrice(productB.stores);

  return (
    <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-6">
      <Breadcrumb
        items={[
          {
            name: `${productA.short_title || productA.title} vs ${productB.short_title || productB.title}`,
            href: `/karsilastir/${ids}`,
          },
        ]}
      />

      <h1 className="mt-6 text-2xl md:text-3xl font-bold text-gray-900">
        {productA.short_title || productA.title} vs{" "}
        {productB.short_title || productB.title}
      </h1>
      <p className="mt-2 text-gray-500">
        Hangisi daha ucuz? Fiyat karşılaştırması ve analiz.
      </p>

      {/* Side by side comparison */}
      <div className="mt-8 grid grid-cols-1 md:grid-cols-2 gap-6">
        {[
          { product: productA, price: priceA, history: historyA },
          { product: productB, price: priceB, history: historyB },
        ].map(({ product, price, history }) => {
          const isCheaper =
            priceA && priceB
              ? price === Math.min(priceA, priceB) && priceA !== priceB
              : false;

          return (
            <div
              key={product.id}
              className={`bg-white border rounded-xl p-6 ${
                isCheaper ? "border-success ring-2 ring-success/20" : "border-gray-200"
              }`}
            >
              {isCheaper && (
                <span className="inline-block bg-success text-white text-xs font-bold px-2 py-1 rounded mb-4">
                  DAHA UCUZ
                </span>
              )}
              <div className="relative h-40 mb-4">
                <ProductImage
                  src={product.image_url}
                  alt={product.title}
                  fill
                  className="object-contain"
                  sizes="(max-width: 768px) 100vw, 50vw"
                />
              </div>
              <h2 className="text-lg font-bold text-gray-900 text-center">
                {product.short_title || product.title}
              </h2>
              {product.brand && (
                <p className="text-sm text-gray-500 text-center mt-1">
                  {product.brand}
                </p>
              )}
              <p className="text-2xl font-bold text-brand text-center mt-4">
                {formatPrice(price)}
              </p>
              <p className="text-xs text-gray-400 text-center">
                {product.stores.filter((s) => s.in_stock).length} mağazada mevcut
              </p>

              {history.length > 1 && (
                <div className="mt-4">
                  <PriceHistoryChart data={history} />
                </div>
              )}
            </div>
          );
        })}
      </div>
    </div>
  );
}
