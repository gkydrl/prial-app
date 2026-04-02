import { notFound } from "next/navigation";
import type { Metadata } from "next";
import Link from "next/link";
import { getProduct, getProductPriceHistory } from "@/lib/api";
import type { ProductResponse, ProductStoreResponse, StoreName } from "@/lib/api";
import { comparisonMeta } from "@/lib/metaTags";
import { productSlug } from "@/lib/slugify";
import { Breadcrumb } from "@/components/layout/Breadcrumb";
import { ProductImage } from "@/components/product/ProductImage";
import { SignalBadge } from "@/components/ui/SignalBadge";
import { FAQSchema } from "@/components/seo/FAQSchema";
import dynamic from "next/dynamic";

const PriceHistoryChart = dynamic(
  () => import("@/components/product/PriceHistoryChart").then((m) => m.PriceHistoryChart),
  { loading: () => <div className="h-[400px] bg-gray-50 rounded-xl animate-pulse" /> }
);
import { formatPrice } from "@/lib/formatPrice";
import { storeLabel } from "@/lib/stores";

interface Props {
  params: Promise<{ ids: string }>;
}

function parseIds(idsParam: string): { idA: string; idB: string; slug: string } | null {
  const vsMatch = idsParam.match(/^([a-f0-9-]+)-vs-([a-f0-9-]+)/);
  if (!vsMatch) return null;
  return { idA: vsMatch[1], idB: vsMatch[2], slug: idsParam };
}

function getBestPrice(stores: ProductStoreResponse[]): number | null {
  const active = stores.filter((s) => s.current_price != null && s.in_stock);
  return active.length ? Math.min(...active.map((s) => s.current_price!)) : null;
}

function getBestStore(stores: ProductStoreResponse[]): ProductStoreResponse | null {
  const active = stores.filter((s) => s.current_price != null && s.in_stock);
  return active.length
    ? active.reduce((a, b) => ((a.current_price ?? Infinity) < (b.current_price ?? Infinity) ? a : b))
    : null;
}

/** Build "Hangisini almalıyım?" paragraph from two products' reasoning */
function buildVerdictText(a: ProductResponse, b: ProductResponse): string | null {
  const nameA = a.short_title || a.title;
  const nameB = b.short_title || b.title;
  const priceA = getBestPrice(a.stores);
  const priceB = getBestPrice(b.stores);

  const parts: string[] = [];

  if (priceA && priceB) {
    if (priceA < priceB) {
      parts.push(`${nameA}, ${formatPrice(priceA)} ile daha uygun fiyatlı.`);
    } else if (priceB < priceA) {
      parts.push(`${nameB}, ${formatPrice(priceB)} ile daha uygun fiyatlı.`);
    } else {
      parts.push(`Her iki ürün de aynı fiyatta: ${formatPrice(priceA)}.`);
    }
  }

  if (a.recommendation && b.recommendation) {
    if (a.recommendation === "IYI_FIYAT" && b.recommendation !== "IYI_FIYAT") {
      parts.push(`AI analizimize göre ${nameA} şu an iyi fiyatta.`);
    } else if (b.recommendation === "IYI_FIYAT" && a.recommendation !== "IYI_FIYAT") {
      parts.push(`AI analizimize göre ${nameB} şu an iyi fiyatta.`);
    } else if (a.recommendation === "IYI_FIYAT" && b.recommendation === "IYI_FIYAT") {
      parts.push("AI analizimize göre her iki ürün de şu an iyi fiyatta.");
    }
  }

  if (a.reasoning_text) parts.push(a.reasoning_text);
  if (b.reasoning_text) parts.push(b.reasoning_text);

  return parts.length > 0 ? parts.join(" ") : null;
}

/** Find common stores and their price differences */
function buildStoreComparison(a: ProductResponse, b: ProductResponse) {
  const storesA = a.stores.filter((s) => s.current_price != null && s.in_stock);
  const storesB = b.stores.filter((s) => s.current_price != null && s.in_stock);
  const storeMapA = new Map(storesA.map((s) => [s.store, s]));

  const rows: { store: StoreName; priceA: number; priceB: number; diff: number }[] = [];
  for (const sb of storesB) {
    const sa = storeMapA.get(sb.store);
    if (sa && sa.current_price && sb.current_price) {
      rows.push({
        store: sa.store,
        priceA: sa.current_price,
        priceB: sb.current_price,
        diff: sa.current_price - sb.current_price,
      });
    }
  }
  return rows.sort((a, b) => Math.abs(b.diff) - Math.abs(a.diff));
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

  let productA: ProductResponse, productB: ProductResponse;
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

  const priceA = getBestPrice(productA.stores);
  const priceB = getBestPrice(productB.stores);
  const verdictText = buildVerdictText(productA, productB);
  const storeComparison = buildStoreComparison(productA, productB);

  const nameA = productA.short_title || productA.title;
  const nameB = productB.short_title || productB.title;

  // Build FAQ items for comparison
  const comparisonFAQs = {
    title: `${nameA} vs ${nameB}`,
    stores: [...productA.stores, ...productB.stores],
    predicted_direction: productA.predicted_direction,
  };

  return (
    <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-6">
      <Breadcrumb
        items={[
          { name: "Karşılaştır", href: "/karsilastir" },
          {
            name: `${nameA} vs ${nameB}`,
            href: `/karsilastir/${ids}`,
          },
        ]}
      />

      <h1 className="mt-6 text-2xl md:text-3xl font-bold text-gray-900">
        {nameA} vs {nameB}
      </h1>
      <p className="mt-2 text-gray-500">
        Hangisi daha ucuz? Fiyat karşılaştırması ve AI analiz.
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
          const catSlug = product.category_slug || "urun";
          const detailHref = `/${catSlug}/${productSlug(product.title, product.id)}`;

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
              <Link href={detailHref}>
                <h2 className="text-lg font-bold text-gray-900 text-center hover:text-brand transition-colors">
                  {product.short_title || product.title}
                </h2>
              </Link>
              {product.brand && (
                <p className="text-sm text-gray-500 text-center mt-1">
                  {product.brand}
                </p>
              )}

              {/* AI Recommendation Badge */}
              {product.recommendation && (
                <div className="flex justify-center mt-3">
                  <SignalBadge recommendation={product.recommendation} size="md" />
                </div>
              )}

              <p className="text-2xl font-bold text-brand text-center mt-4">
                {formatPrice(price)}
              </p>
              <p className="text-xs text-gray-400 text-center">
                {product.stores.filter((s) => s.in_stock).length} mağazada mevcut
              </p>

              {/* Link to product detail */}
              <Link
                href={detailHref}
                className="mt-3 block text-center text-sm text-brand hover:underline font-medium"
              >
                Detaylı İncele
              </Link>

              {history.length > 1 && (
                <div className="mt-4">
                  <PriceHistoryChart data={history} />
                </div>
              )}
            </div>
          );
        })}
      </div>

      {/* "Hangisini Almalıyım?" Section */}
      {verdictText && (
        <section className="mt-10">
          <h2 className="text-2xl font-bold text-gray-900 mb-4">
            {nameA} mı {nameB} mi Almalıyım?
          </h2>
          <div className="bg-white border border-gray-200 rounded-xl p-6">
            <p className="text-gray-700 leading-relaxed">{verdictText}</p>
          </div>
        </section>
      )}

      {/* Store Price Comparison Table */}
      {storeComparison.length > 0 && (
        <section className="mt-10">
          <h2 className="text-2xl font-bold text-gray-900 mb-4">
            Mağaza Bazlı Fiyat Karşılaştırması
          </h2>
          <div className="overflow-x-auto">
            <table className="w-full border-collapse bg-white border border-gray-200 rounded-xl overflow-hidden">
              <thead>
                <tr className="bg-gray-50">
                  <th className="text-left px-4 py-3 text-sm font-semibold text-gray-700">Mağaza</th>
                  <th className="text-right px-4 py-3 text-sm font-semibold text-gray-700">{nameA}</th>
                  <th className="text-right px-4 py-3 text-sm font-semibold text-gray-700">{nameB}</th>
                  <th className="text-right px-4 py-3 text-sm font-semibold text-gray-700">Fark</th>
                </tr>
              </thead>
              <tbody>
                {storeComparison.map((row) => (
                  <tr key={row.store} className="border-t border-gray-100">
                    <td className="px-4 py-3 text-sm text-gray-700">{storeLabel(row.store)}</td>
                    <td className="px-4 py-3 text-sm text-right font-medium text-gray-900">
                      {formatPrice(row.priceA)}
                    </td>
                    <td className="px-4 py-3 text-sm text-right font-medium text-gray-900">
                      {formatPrice(row.priceB)}
                    </td>
                    <td className={`px-4 py-3 text-sm text-right font-bold ${
                      row.diff > 0 ? "text-danger" : row.diff < 0 ? "text-success" : "text-gray-500"
                    }`}>
                      {row.diff > 0 ? "+" : ""}{formatPrice(Math.abs(row.diff))}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </section>
      )}

      {/* FAQ Schema */}
      <FAQSchema
        title={`${nameA} vs ${nameB}`}
        stores={comparisonFAQs.stores}
        predicted_direction={comparisonFAQs.predicted_direction}
        recommendation={productA.recommendation}
        reasoningText={verdictText}
      />
    </div>
  );
}
