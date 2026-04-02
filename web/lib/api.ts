const API_BASE = process.env.NEXT_PUBLIC_API_BASE_URL ?? "https://prial-app-production.up.railway.app/api/v1";

interface FetchOptions {
  revalidate?: number;
  tags?: string[];
}

async function apiFetch<T>(path: string, opts: FetchOptions = {}): Promise<T> {
  const url = `${API_BASE}${path}`;
  const controller = new AbortController();
  const timeout = setTimeout(() => controller.abort(), 10_000); // 10s timeout

  try {
    const res = await fetch(url, {
      next: {
        revalidate: opts.revalidate,
        tags: opts.tags,
      },
      signal: controller.signal,
    });

    if (!res.ok) {
      throw new Error(`API error ${res.status}: ${url}`);
    }

    return res.json() as Promise<T>;
  } finally {
    clearTimeout(timeout);
  }
}

// --- Types ---

export type StoreName =
  | "trendyol"
  | "hepsiburada"
  | "amazon"
  | "n11"
  | "ciceksepeti"
  | "mediamarkt"
  | "teknosa"
  | "vatan"
  | "other";

export interface ProductStoreResponse {
  id: string;
  store: StoreName;
  url: string;
  current_price: number | null;
  original_price: number | null;
  currency: string;
  discount_percent: number | null;
  in_stock: boolean;
  last_checked_at: string | null;
  variant_id: string | null;
}

export interface ProductVariantResponse {
  id: string;
  title: string | null;
  attributes: Record<string, string> | null;
  image_url: string | null;
  alarm_count: number;
  lowest_price_ever: number | null;
  stores: ProductStoreResponse[];
}

export interface ProductResponse {
  id: string;
  title: string;
  short_title: string | null;
  brand: string | null;
  description: string | null;
  image_url: string | null;
  lowest_price_ever: number | null;
  l1y_lowest_price: number | null;
  l1y_highest_price: number | null;
  akakce_url: string | null;
  alarm_count: number;
  recommendation: "IYI_FIYAT" | "FIYAT_DUSEBILIR" | "FIYAT_YUKSELISTE" | null;
  reasoning_text: string | null;
  reasoning_pros: string[] | null;
  reasoning_cons: string[] | null;
  predicted_direction: "UP" | "DOWN" | "STABLE" | null;
  prediction_confidence: number | null;
  stores: ProductStoreResponse[];
  variants: ProductVariantResponse[];
  category_id: string | null;
  category_slug: string | null;
  created_at: string;
}

export interface PredictionResponse {
  status: "ok" | "no_prediction";
  recommendation?: "IYI_FIYAT" | "FIYAT_DUSEBILIR" | "FIYAT_YUKSELISTE";
  confidence?: number;
  reasoning_text?: string;
  reasoning_pros?: string[];
  reasoning_cons?: string[];
  predicted_direction?: "UP" | "DOWN" | "STABLE";
  current_price?: number;
}

export interface CategoryResponse {
  id: string;
  name: string;
  slug: string;
  image_url: string | null;
  product_count?: number;
  children: CategoryResponse[];
}

export interface PriceHistoryPoint {
  price: number;
  recorded_at: string;
}

export interface HomeStats {
  user_count: number;
  active_alarm_count: number;
  triggered_count: number;
}

export interface DailyDealProduct extends ProductResponse {
  price_drop_percent?: number;
}

// --- API Functions ---

export async function getCategories(revalidate = 3600): Promise<CategoryResponse[]> {
  return apiFetch<CategoryResponse[]>("/discover/categories", { revalidate });
}

export async function getCategoryProducts(
  slug: string,
  page = 1,
  pageSize = 24,
  sort = "alarm_count",
  revalidate = 3600
): Promise<ProductResponse[]> {
  return apiFetch<ProductResponse[]>(
    `/discover/categories/${slug}/products?page=${page}&page_size=${pageSize}&sort=${sort}`,
    { revalidate, tags: [`category-${slug}`] }
  );
}

export async function getProduct(id: string, revalidate = 900): Promise<ProductResponse> {
  return apiFetch<ProductResponse>(`/products/${id}`, {
    revalidate,
    tags: [`product-${id}`],
  });
}

export async function getProductPriceHistory(
  productId: string,
  storeId?: string,
  revalidate = 900
): Promise<PriceHistoryPoint[]> {
  const params = storeId ? `?store_id=${storeId}` : "";
  return apiFetch<PriceHistoryPoint[]>(
    `/products/${productId}/price-history${params}`,
    { revalidate }
  );
}

export async function getProducts(
  limit = 50,
  category?: string,
  revalidate = 1800
): Promise<ProductResponse[]> {
  const params = category ? `?limit=${limit}&category=${category}` : `?limit=${limit}`;
  return apiFetch<ProductResponse[]>(`/products${params}`, { revalidate });
}

export async function getDailyDeals(revalidate = 1800): Promise<DailyDealProduct[]> {
  return apiFetch<DailyDealProduct[]>("/home/daily-deals", { revalidate });
}

export async function getTopDrops(revalidate = 1800): Promise<DailyDealProduct[]> {
  return apiFetch<DailyDealProduct[]>("/home/top-drops", { revalidate });
}

export async function getMostAlarmed(revalidate = 1800): Promise<ProductResponse[]> {
  return apiFetch<ProductResponse[]>("/home/most-alarmed", { revalidate });
}

export async function getHomeStats(revalidate = 1800): Promise<HomeStats> {
  return apiFetch<HomeStats>("/home/stats", { revalidate });
}

export async function searchProducts(
  query: string,
  page = 1,
  pageSize = 24
): Promise<ProductResponse[]> {
  return apiFetch<ProductResponse[]>(
    `/discover/search?q=${encodeURIComponent(query)}&page=${page}&page_size=${pageSize}`,
    { revalidate: 0 }
  );
}

export async function getProductPrediction(productId: string): Promise<PredictionResponse | null> {
  try {
    return await apiFetch<PredictionResponse>(`/products/${productId}/prediction`, {
      revalidate: 900,
    });
  } catch {
    return null;
  }
}

export async function getAIPicks(revalidate = 1800): Promise<ProductResponse[]> {
  return apiFetch<ProductResponse[]>("/home/ai-picks?limit=10", { revalidate });
}

export async function getAIWaitPicks(revalidate = 1800): Promise<ProductResponse[]> {
  return apiFetch<ProductResponse[]>("/home/ai-wait-picks?limit=10", { revalidate });
}

// --- Filters ---

/** Filter out products without image, price, or AI recommendation */
export function filterDisplayable(products: ProductResponse[]): ProductResponse[] {
  return products.filter((p) => {
    if (!p.image_url) return false;
    if (!p.recommendation) return false;
    const hasPrice = p.stores.some((s) => s.current_price != null && s.in_stock);
    if (!hasPrice) return false;
    return true;
  });
}
