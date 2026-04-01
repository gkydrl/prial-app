import { notFound } from "next/navigation";
import type { Metadata } from "next";
import { getCategories, getCategoryProducts, filterDisplayable } from "@/lib/api";
import { categoryMeta } from "@/lib/metaTags";
import { Breadcrumb } from "@/components/layout/Breadcrumb";
import { ProductCard } from "@/components/product/ProductCard";
import { ItemListSchema } from "@/components/seo/ItemListSchema";

interface Props {
  params: Promise<{ categorySlug: string }>;
  searchParams: Promise<{ page?: string; sort?: string }>;
}

export async function generateMetadata({ params, searchParams }: Props): Promise<Metadata> {
  const { categorySlug } = await params;
  const sp = await searchParams;
  const categories = await getCategories().catch(() => []);
  const category = categories.find((c) => c.slug === categorySlug);
  if (!category) return {};

  const meta = categoryMeta(category.name, category.slug);
  const page = parseInt(sp.page ?? "1", 10) || 1;
  const sort = sp.sort ?? "alarm_count";

  // Noindex paginated or sorted pages to avoid duplicate content
  if (sort !== "alarm_count" || page > 1) {
    meta.robots = { index: false, follow: true };
  }

  return meta;
}

export const revalidate = 3600; // 1 hour

export default async function CategoryPage({ params, searchParams }: Props) {
  const { categorySlug } = await params;
  const sp = await searchParams;
  const page = Math.max(1, parseInt(sp.page ?? "1", 10) || 1);
  const sort = sp.sort ?? "alarm_count";

  const categories = await getCategories().catch(() => []);
  const category = categories.find((c) => c.slug === categorySlug);
  if (!category) notFound();

  const rawProducts = await getCategoryProducts(categorySlug, page, 48, sort).catch(
    () => []
  );

  const products = filterDisplayable(rawProducts);

  if (!rawProducts) notFound();

  return (
    <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-6">
      <ItemListSchema
        categoryName={category.name}
        categorySlug={category.slug}
        products={products}
      />
      <Breadcrumb items={[{ name: category.name, href: `/${category.slug}` }]} />

      <div className="mt-6">
        <h1 className="text-3xl font-bold text-gray-900">
          {category.name} Fiyatları
        </h1>
        {products.length > 0 && (
          <p className="mt-2 text-gray-500">
            {products.length} ürün bulundu
          </p>
        )}
      </div>

      {/* Sort */}
      <div className="mt-6 flex items-center gap-2">
        <span className="text-sm text-gray-500">Sırala:</span>
        <SortLink slug={categorySlug} sort="alarm_count" current={sort} label="Popüler" />
        <SortLink slug={categorySlug} sort="price_asc" current={sort} label="En Ucuz" />
        <SortLink slug={categorySlug} sort="price_desc" current={sort} label="En Pahalı" />
        <SortLink slug={categorySlug} sort="newest" current={sort} label="En Yeni" />
      </div>

      {/* Product Grid */}
      <div className="mt-6 grid grid-cols-2 md:grid-cols-3 lg:grid-cols-4 xl:grid-cols-5 gap-4">
        {products.map((product) => (
          <ProductCard key={product.id} product={product} categorySlug={categorySlug} />
        ))}
      </div>

      {products.length === 0 && (
        <p className="text-center text-gray-500 py-12">
          Bu kategoride henüz ürün bulunmuyor.
        </p>
      )}

      {/* Popular Brands */}
      {(() => {
        const brands = [...new Set(products.map((p) => p.brand).filter(Boolean))] as string[];
        if (brands.length === 0) return null;
        return (
          <section className="mt-10 mb-6">
            <h2 className="text-lg font-bold text-gray-900 mb-3">
              {category.name} Markaları
            </h2>
            <div className="flex flex-wrap gap-2">
              {brands.slice(0, 15).map((brand) => (
                <a
                  key={brand}
                  href={`/marka/${brand.toLowerCase().replace(/\s+/g, "-")}`}
                  className="px-3 py-1.5 text-sm bg-gray-100 text-gray-700 rounded-lg hover:bg-brand/10 hover:text-brand transition-colors"
                >
                  {brand}
                </a>
              ))}
            </div>
          </section>
        );
      })()}
    </div>
  );
}

function SortLink({
  slug,
  sort,
  current,
  label,
}: {
  slug: string;
  sort: string;
  current: string;
  label: string;
}) {
  const isActive = sort === current;
  return (
    <a
      href={`/${slug}?sort=${sort}`}
      className={`px-3 py-1.5 rounded-lg text-sm transition-colors ${
        isActive
          ? "bg-brand text-white"
          : "bg-gray-100 text-gray-600 hover:bg-gray-200"
      }`}
    >
      {label}
    </a>
  );
}
