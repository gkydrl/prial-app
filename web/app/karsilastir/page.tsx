import type { Metadata } from "next";
import Link from "next/link";
import { getCategories, getComparisons } from "@/lib/api";
import type { ComparisonPair } from "@/lib/api";
import { Breadcrumb } from "@/components/layout/Breadcrumb";
import { ProductImage } from "@/components/product/ProductImage";
import { formatPrice } from "@/lib/formatPrice";
import { SignalBadge } from "@/components/ui/SignalBadge";

const SITE_NAME = "Prial";
const CURRENT_YEAR = new Date().getFullYear();

export const metadata: Metadata = {
  title: `Ürün Karşılaştırma | En Popüler Karşılaştırmalar ${CURRENT_YEAR} | ${SITE_NAME}`,
  description: `En popüler ürün karşılaştırmaları ${CURRENT_YEAR}. Telefon, laptop, tablet ve daha fazlasını karşılaştır. AI destekli fiyat analizi ile hangisinin daha iyi olduğunu öğren.`,
};

export const revalidate = 21600; // 6 hours

function getBestPrice(stores: { current_price: number | null; in_stock: boolean }[]): number | null {
  const active = stores.filter((s) => s.current_price != null && s.in_stock);
  return active.length ? Math.min(...active.map((s) => s.current_price!)) : null;
}

function ComparisonCard({ pair }: { pair: ComparisonPair }) {
  const { product_a: a, product_b: b } = pair;
  const shortA = a.id.replace(/-/g, "").slice(0, 8);
  const shortB = b.id.replace(/-/g, "").slice(0, 8);
  const href = `/karsilastir/${shortA}-vs-${shortB}`;
  const priceA = getBestPrice(a.stores);
  const priceB = getBestPrice(b.stores);

  return (
    <Link
      href={href}
      className="flex items-center gap-4 p-4 bg-white border border-gray-200 rounded-xl hover:shadow-md hover:border-brand/30 transition-all group"
    >
      {/* Product A */}
      <div className="flex items-center gap-3 flex-1 min-w-0">
        <div className="relative w-14 h-14 flex-shrink-0">
          <ProductImage
            src={a.image_url}
            alt={a.title}
            fill
            className="object-contain"
            sizes="56px"
          />
        </div>
        <div className="min-w-0">
          <p className="text-sm font-medium text-gray-900 truncate">
            {a.short_title || a.title}
          </p>
          <p className="text-sm font-bold text-brand">{formatPrice(priceA)}</p>
          {a.recommendation && (
            <SignalBadge recommendation={a.recommendation} size="sm" />
          )}
        </div>
      </div>

      {/* VS divider */}
      <span className="text-xs font-bold text-gray-400 flex-shrink-0">VS</span>

      {/* Product B */}
      <div className="flex items-center gap-3 flex-1 min-w-0">
        <div className="relative w-14 h-14 flex-shrink-0">
          <ProductImage
            src={b.image_url}
            alt={b.title}
            fill
            className="object-contain"
            sizes="56px"
          />
        </div>
        <div className="min-w-0">
          <p className="text-sm font-medium text-gray-900 truncate">
            {b.short_title || b.title}
          </p>
          <p className="text-sm font-bold text-brand">{formatPrice(priceB)}</p>
          {b.recommendation && (
            <SignalBadge recommendation={b.recommendation} size="sm" />
          )}
        </div>
      </div>

      {/* Arrow */}
      <svg
        className="w-5 h-5 text-gray-300 group-hover:text-brand flex-shrink-0 transition-colors"
        fill="none"
        viewBox="0 0 24 24"
        stroke="currentColor"
        strokeWidth={2}
      >
        <path strokeLinecap="round" strokeLinejoin="round" d="M9 5l7 7-7 7" />
      </svg>
    </Link>
  );
}

export default async function ComparisonsIndexPage() {
  const [categories, allPairs] = await Promise.all([
    getCategories().catch(() => []),
    getComparisons(undefined, 50).catch(() => []),
  ]);

  // Group pairs by category (use product_a's category_slug as proxy)
  const grouped: Record<string, { name: string; pairs: ComparisonPair[] }> = {};

  for (const pair of allPairs) {
    const catSlug = pair.product_a.category_slug || "diger";
    if (!grouped[catSlug]) {
      // Try to find category name
      const cat = categories.find((c) => c.slug === catSlug);
      const name = cat?.name || catSlug.split("-").map((w) => w.charAt(0).toUpperCase() + w.slice(1)).join(" ");
      grouped[catSlug] = { name, pairs: [] };
    }
    grouped[catSlug].pairs.push(pair);
  }

  const categoryGroups = Object.entries(grouped);

  return (
    <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-6">
      <Breadcrumb
        items={[{ name: "Karşılaştır", href: "/karsilastir" }]}
      />

      <h1 className="mt-6 text-2xl md:text-3xl font-bold text-gray-900">
        Ürün Karşılaştırma
      </h1>
      <p className="mt-2 text-gray-500">
        En popüler ürünleri yan yana karşılaştır. AI destekli fiyat analizi ile en doğru kararı ver.
      </p>

      {categoryGroups.length === 0 ? (
        <p className="mt-8 text-gray-400">Henüz karşılaştırma verisi yok.</p>
      ) : (
        <div className="mt-8 space-y-10">
          {categoryGroups.map(([slug, { name, pairs }]) => (
            <section key={slug}>
              <h2 className="text-xl font-bold text-gray-900 mb-4">{name}</h2>
              <div className="space-y-3">
                {pairs.map((pair, i) => (
                  <ComparisonCard key={i} pair={pair} />
                ))}
              </div>
            </section>
          ))}
        </div>
      )}
    </div>
  );
}
