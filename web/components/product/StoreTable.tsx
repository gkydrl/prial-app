import type { ProductStoreResponse } from "@/lib/api";
import { formatPrice, formatDiscount } from "@/lib/formatPrice";
import { storeLabel, storeColor } from "@/lib/stores";

export function StoreTable({ stores }: { stores: ProductStoreResponse[] }) {
  const sorted = [...stores]
    .filter((s) => s.current_price != null)
    .sort((a, b) => {
      // In-stock first
      if (a.in_stock !== b.in_stock) return a.in_stock ? -1 : 1;
      return (a.current_price ?? Infinity) - (b.current_price ?? Infinity);
    });

  if (sorted.length === 0) {
    return (
      <p className="text-gray-500 text-sm">
        Şu an mağaza fiyat bilgisi bulunmuyor.
      </p>
    );
  }

  return (
    <div className="overflow-x-auto">
      <table className="w-full">
        <thead>
          <tr className="border-b border-gray-200 text-left text-sm text-gray-500">
            <th className="pb-3 font-medium">Mağaza</th>
            <th className="pb-3 font-medium">Fiyat</th>
            <th className="pb-3 font-medium hidden sm:table-cell">
              İndirim
            </th>
            <th className="pb-3 font-medium hidden md:table-cell">Durum</th>
            <th className="pb-3 font-medium text-right">İşlem</th>
          </tr>
        </thead>
        <tbody className="divide-y divide-gray-100">
          {sorted.map((store, i) => (
            <tr
              key={store.id}
              className={`${!store.in_stock ? "opacity-50" : ""} ${
                i === 0 ? "bg-green-50/50" : ""
              }`}
            >
              <td className="py-4">
                <div className="flex items-center gap-2">
                  <span
                    className="w-2 h-2 rounded-full flex-shrink-0"
                    style={{ backgroundColor: storeColor(store.store) }}
                  />
                  <span className="font-medium text-gray-900 text-sm">
                    {storeLabel(store.store)}
                  </span>
                </div>
              </td>
              <td className="py-4">
                <div>
                  <span
                    className={`font-bold ${
                      i === 0 && store.in_stock
                        ? "text-success text-lg"
                        : "text-gray-900"
                    }`}
                  >
                    {formatPrice(store.current_price)}
                  </span>
                  {store.original_price &&
                    store.original_price > (store.current_price ?? 0) && (
                      <span className="ml-2 text-xs text-gray-400 line-through">
                        {formatPrice(store.original_price)}
                      </span>
                    )}
                </div>
              </td>
              <td className="py-4 hidden sm:table-cell">
                {store.discount_percent && store.discount_percent > 0 ? (
                  <span className="inline-block bg-danger/10 text-danger text-xs font-medium px-2 py-1 rounded">
                    {formatDiscount(store.discount_percent)}
                  </span>
                ) : (
                  <span className="text-gray-300 text-sm">—</span>
                )}
              </td>
              <td className="py-4 hidden md:table-cell">
                <span
                  className={`text-xs font-medium ${
                    store.in_stock ? "text-success" : "text-gray-400"
                  }`}
                >
                  {store.in_stock ? "Stokta" : "Tükendi"}
                </span>
              </td>
              <td className="py-4 text-right">
                <a
                  href={store.url}
                  target="_blank"
                  rel="noopener noreferrer nofollow"
                  className={`inline-block text-sm font-medium px-4 py-2 rounded-lg transition-colors ${
                    i === 0 && store.in_stock
                      ? "bg-brand text-white hover:bg-brand-dark"
                      : "bg-gray-100 text-gray-700 hover:bg-gray-200"
                  }`}
                >
                  Mağazaya Git
                </a>
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
