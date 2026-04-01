export function formatPrice(price: number | null | undefined): string {
  if (price == null) return "—";
  return new Intl.NumberFormat("tr-TR", {
    style: "currency",
    currency: "TRY",
    minimumFractionDigits: 0,
    maximumFractionDigits: 0,
  }).format(price);
}

export function formatPriceCompact(price: number): string {
  if (price >= 1_000_000) {
    return `₺${(price / 1_000_000).toFixed(1)}M`;
  }
  if (price >= 1_000) {
    return `₺${(price / 1_000).toFixed(1)}B`;
  }
  return formatPrice(price);
}

export function formatDiscount(percent: number | null | undefined): string {
  if (percent == null || percent <= 0) return "";
  return `%${percent}`;
}
