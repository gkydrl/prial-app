import type { Metadata } from "next";
import { searchProducts, filterDisplayable } from "@/lib/api";
import { ProductCard } from "@/components/product/ProductCard";

interface Props {
  searchParams: Promise<{ q?: string; page?: string }>;
}

export const metadata: Metadata = {
  robots: { index: false, follow: false },
};

export default async function SearchPage({ searchParams }: Props) {
  const sp = await searchParams;
  const query = sp.q ?? "";
  const page = Math.max(1, parseInt(sp.page ?? "1", 10) || 1);

  const rawProducts = query
    ? await searchProducts(query, page, 24).catch(() => [])
    : [];
  const products = filterDisplayable(rawProducts);

  return (
    <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-6">
      <h1 className="text-2xl font-bold text-gray-900">Arama Sonuçları</h1>

      {query && (
        <p className="mt-2 text-gray-500">
          &ldquo;{query}&rdquo; için{" "}
          {products.length > 0 ? `${products.length} sonuç bulundu` : "sonuç bulunamadı"}
        </p>
      )}

      {!query && (
        <p className="mt-4 text-gray-500">Arama yapmak için bir kelime girin.</p>
      )}

      {products.length > 0 && (
        <div className="mt-6 grid grid-cols-2 md:grid-cols-3 lg:grid-cols-4 xl:grid-cols-5 gap-4">
          {products.map((product) => (
            <ProductCard key={product.id} product={product} />
          ))}
        </div>
      )}

      {query && products.length === 0 && (
        <div className="text-center py-12">
          <p className="text-gray-500">
            &ldquo;{query}&rdquo; ile eşleşen ürün bulunamadı.
          </p>
          <p className="text-sm text-gray-400 mt-2">
            Farklı bir arama terimi deneyin.
          </p>
        </div>
      )}
    </div>
  );
}
