"use client";

import type { ProductVariantResponse, ProductStoreResponse } from "@/lib/api";
import { formatPrice } from "@/lib/formatPrice";

interface Props {
  variants: ProductVariantResponse[];
  stores: ProductStoreResponse[];
  categorySlug: string;
}

export function VariantSelector({ variants, stores }: Props) {
  const variantPrices = variants.map((v) => {
    const variantStores = stores.filter(
      (s) => s.variant_id === v.id && s.current_price && s.in_stock
    );
    const lowestPrice = variantStores.length
      ? Math.min(...variantStores.map((s) => s.current_price!))
      : null;
    return { ...v, lowestPrice };
  });

  return (
    <div>
      <h3 className="text-sm font-medium text-gray-700 mb-2">Varyantlar</h3>
      <div className="flex flex-wrap gap-2">
        {variantPrices.map((v) => (
          <div
            key={v.id}
            className="border border-gray-200 rounded-lg px-3 py-2 text-sm hover:border-brand cursor-pointer transition-colors"
          >
            <span className="text-gray-900">{v.title || "Standart"}</span>
            {v.lowestPrice && (
              <span className="ml-2 text-gray-500 text-xs">
                {formatPrice(v.lowestPrice)}
              </span>
            )}
          </div>
        ))}
      </div>
    </div>
  );
}
