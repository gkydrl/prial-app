import type { Metadata } from "next";
import { searchProducts, filterDisplayable } from "@/lib/api";
import { brandMeta } from "@/lib/metaTags";
import { Breadcrumb } from "@/components/layout/Breadcrumb";
import { ProductCard } from "@/components/product/ProductCard";

interface Props {
  params: Promise<{ brandSlug: string }>;
}

function brandName(slug: string): string {
  return slug
    .split("-")
    .map((w) => w.charAt(0).toUpperCase() + w.slice(1))
    .join(" ");
}

export async function generateMetadata({ params }: Props): Promise<Metadata> {
  const { brandSlug } = await params;
  return brandMeta(brandName(brandSlug), brandSlug);
}

export const revalidate = 3600;

export default async function BrandPage({ params }: Props) {
  const { brandSlug } = await params;
  const brand = brandName(brandSlug);

  const rawProducts = await searchProducts(brand, 1, 48).catch(() => []);
  const products = filterDisplayable(rawProducts);

  return (
    <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-6">
      <Breadcrumb
        items={[
          { name: "Markalar", href: "/marka" },
          { name: brand, href: `/marka/${brandSlug}` },
        ]}
      />

      <div className="mt-6">
        <h1 className="text-3xl font-bold text-gray-900">
          {brand} Fiyatları
        </h1>
        <p className="mt-2 text-gray-500">
          Tüm {brand} modelleri ve en ucuz fiyatlar
        </p>
      </div>

      {products.length > 0 ? (
        <div className="mt-6 grid grid-cols-2 md:grid-cols-3 lg:grid-cols-4 xl:grid-cols-5 gap-4">
          {products.map((product) => (
            <ProductCard key={product.id} product={product} />
          ))}
        </div>
      ) : (
        <p className="text-center text-gray-500 py-12">
          Bu markaya ait ürün bulunmadı.
        </p>
      )}
    </div>
  );
}
