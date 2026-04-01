import type { ProductResponse } from "@/lib/api";
import { productSlug } from "@/lib/slugify";

interface ItemListSchemaProps {
  categoryName: string;
  categorySlug: string;
  products: ProductResponse[];
}

export function ItemListSchema({ categoryName, categorySlug, products }: ItemListSchemaProps) {
  const schema = {
    "@context": "https://schema.org",
    "@type": "ItemList",
    name: `${categoryName} Fiyatları`,
    url: `https://prial.io/${categorySlug}`,
    numberOfItems: products.length,
    itemListElement: products.slice(0, 30).map((p, i) => ({
      "@type": "ListItem",
      position: i + 1,
      name: p.title,
      url: `https://prial.io/${categorySlug}/${productSlug(p.title, p.id)}`,
    })),
  };

  return (
    <script
      type="application/ld+json"
      dangerouslySetInnerHTML={{ __html: JSON.stringify(schema) }}
    />
  );
}
