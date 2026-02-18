// ─── Auth ────────────────────────────────────────────────────────────────────

export interface TokenResponse {
  access_token: string;
  refresh_token: string;
  token_type: string;
}

// ─── User ────────────────────────────────────────────────────────────────────

export interface UserResponse {
  id: string;
  email: string;
  full_name: string | null;
  avatar_url: string | null;
  push_notifications_enabled: boolean;
  email_notifications_enabled: boolean;
  notify_on_price_drop: boolean;
  notify_on_back_in_stock: boolean;
  is_verified: boolean;
  created_at: string;
}

export interface UserUpdatePreferences {
  full_name?: string;
  push_notifications_enabled?: boolean;
  email_notifications_enabled?: boolean;
  notify_on_price_drop?: boolean;
  notify_on_back_in_stock?: boolean;
}

// ─── Product ─────────────────────────────────────────────────────────────────

export type StoreName =
  | 'trendyol'
  | 'hepsiburada'
  | 'amazon'
  | 'n11'
  | 'ciceksepeti'
  | 'mediamarkt'
  | 'teknosa'
  | 'vatan'
  | 'other';

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
}

export interface ProductResponse {
  id: string;
  title: string;
  brand: string | null;
  description: string | null;
  image_url: string | null;
  lowest_price_ever: number | null;
  alarm_count: number;
  stores: ProductStoreResponse[];
  created_at: string;
}

export interface PriceHistoryPoint {
  price: number;
  recorded_at: string;
}

export interface CategoryResponse {
  id: string;
  name: string;
  slug: string;
  image_url: string | null;
  children: CategoryResponse[];
}

// ─── Alarm ───────────────────────────────────────────────────────────────────

export type AlarmStatus = 'active' | 'triggered' | 'paused' | 'deleted';

export interface AlarmResponse {
  id: string;
  target_price: number;
  status: AlarmStatus;
  triggered_price: number | null;
  triggered_at: string | null;
  created_at: string;
  product: ProductResponse;
  product_store: ProductStoreResponse | null;
}

export interface AlarmUpdatePayload {
  target_price?: number;
  status?: AlarmStatus;
}

// ─── Home ────────────────────────────────────────────────────────────────────

export interface TopDropResponse {
  store: ProductStoreResponse;
  price_24h_ago: number;
  price_now: number;
  drop_amount: number;
  drop_percent: number;
}

// ─── API Responses ───────────────────────────────────────────────────────────

export interface AddProductResponse {
  message: string;
  alarm_id?: string;
}

export interface PaginatedParams {
  page?: number;
  page_size?: number;
}
