import type { StoreName } from "./api";

interface StoreInfo {
  label: string;
  color: string;
  referer?: string;
}

export const STORE_INFO: Record<StoreName, StoreInfo> = {
  trendyol: { label: "Trendyol", color: "#F27A1A", referer: "https://www.trendyol.com/" },
  hepsiburada: { label: "Hepsiburada", color: "#FF6000", referer: "https://www.hepsiburada.com/" },
  amazon: { label: "Amazon", color: "#FF9900" },
  n11: { label: "n11", color: "#6B21A8" },
  ciceksepeti: { label: "Çiçeksepeti", color: "#E11D48" },
  mediamarkt: { label: "MediaMarkt", color: "#CC0000", referer: "https://www.mediamarkt.com.tr/" },
  teknosa: { label: "Teknosa", color: "#1D4ED8" },
  vatan: { label: "Vatan", color: "#DC2626" },
  other: { label: "Diğer", color: "#6B7280" },
};

export function storeLabel(name: StoreName): string {
  return STORE_INFO[name]?.label ?? name;
}

export function storeColor(name: StoreName): string {
  return STORE_INFO[name]?.color ?? "#6B7280";
}
