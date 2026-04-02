import type { StoreName } from "./api";

interface StoreInfo {
  label: string;
  color: string;
  referer?: string;
  logo: string;
  shipping: string;
  installment: string;
}

export const STORE_INFO: Record<StoreName, StoreInfo> = {
  trendyol: {
    label: "Trendyol",
    color: "#F27A1A",
    referer: "https://www.trendyol.com/",
    logo: "https://cdn.dsmcdn.com/web/production/favicon.ico",
    shipping: "Ücretsiz kargo",
    installment: "12 aya varan taksit",
  },
  hepsiburada: {
    label: "Hepsiburada",
    color: "#FF6000",
    referer: "https://www.hepsiburada.com/",
    logo: "https://images.hepsiburada.net/assets/sfrontend/images/hepsiburada-logo__light.png",
    shipping: "Ücretsiz kargo",
    installment: "9 aya varan taksit",
  },
  amazon: {
    label: "Amazon",
    color: "#FF9900",
    logo: "https://www.amazon.com.tr/favicon.ico",
    shipping: "Prime ile ücretsiz kargo",
    installment: "6 aya varan taksit",
  },
  n11: {
    label: "n11",
    color: "#6B21A8",
    logo: "https://www.n11.com/favicon.ico",
    shipping: "Kargo satıcıya göre değişir",
    installment: "12 aya varan taksit",
  },
  ciceksepeti: {
    label: "Çiçeksepeti",
    color: "#E11D48",
    logo: "https://www.ciceksepeti.com/favicon.ico",
    shipping: "Ücretsiz kargo",
    installment: "6 aya varan taksit",
  },
  mediamarkt: {
    label: "MediaMarkt",
    color: "#CC0000",
    referer: "https://www.mediamarkt.com.tr/",
    logo: "https://www.mediamarkt.com.tr/favicon.ico",
    shipping: "Ücretsiz kargo",
    installment: "12 aya varan taksit",
  },
  teknosa: {
    label: "Teknosa",
    color: "#1D4ED8",
    logo: "https://www.teknosa.com/favicon.ico",
    shipping: "Ücretsiz kargo",
    installment: "12 aya varan taksit",
  },
  vatan: {
    label: "Vatan",
    color: "#DC2626",
    logo: "https://www.vatanbilgisayar.com/favicon.ico",
    shipping: "Ücretsiz kargo",
    installment: "12 aya varan taksit",
  },
  other: {
    label: "Diğer",
    color: "#6B7280",
    logo: "",
    shipping: "Kargo bilgisi yok",
    installment: "",
  },
};

export function storeLabel(name: StoreName): string {
  return STORE_INFO[name]?.label ?? name;
}

export function storeColor(name: StoreName): string {
  return STORE_INFO[name]?.color ?? "#6B7280";
}

export function storeLogo(name: StoreName): string {
  return STORE_INFO[name]?.logo ?? "";
}

export function storeShipping(name: StoreName): string {
  return STORE_INFO[name]?.shipping ?? "";
}

export function storeInstallment(name: StoreName): string {
  return STORE_INFO[name]?.installment ?? "";
}
