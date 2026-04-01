const API_BASE = process.env.NEXT_PUBLIC_API_BASE_URL ?? "https://prial-app-production.up.railway.app/api/v1";

const TOKEN_KEY = "prial_access_token";
const REFRESH_KEY = "prial_refresh_token";

interface SocialLoginResponse {
  access_token: string;
  refresh_token: string;
  token_type: string;
  is_new_user: boolean;
  needs_consent: boolean;
}

interface UserResponse {
  id: string;
  email: string;
  full_name: string | null;
  avatar_url: string | null;
  is_verified: boolean;
  auth_provider: string | null;
  has_completed_consent: boolean;
}

export async function socialLogin(
  provider: "google" | "apple",
  idToken: string,
  fullName?: string
): Promise<SocialLoginResponse> {
  const res = await fetch(`${API_BASE}/auth/social`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ provider, id_token: idToken, full_name: fullName }),
  });

  if (!res.ok) {
    const data = await res.json().catch(() => ({}));
    throw new Error(data.detail ?? "Giriş başarısız");
  }

  const data: SocialLoginResponse = await res.json();
  if (typeof window !== "undefined") {
    localStorage.setItem(TOKEN_KEY, data.access_token);
    localStorage.setItem(REFRESH_KEY, data.refresh_token);
  }
  return data;
}

export async function saveConsent(prefs: {
  push_notifications_enabled: boolean;
  email_notifications_enabled: boolean;
  notify_on_price_drop: boolean;
  notify_on_back_in_stock: boolean;
}): Promise<void> {
  const token = getAccessToken();
  if (!token) throw new Error("Giriş yapılmamış");

  const res = await fetch(`${API_BASE}/auth/consent`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      Authorization: `Bearer ${token}`,
    },
    body: JSON.stringify(prefs),
  });

  if (!res.ok) {
    const data = await res.json().catch(() => ({}));
    throw new Error(data.detail ?? "Tercihler kaydedilemedi");
  }
}

export async function fetchMe(): Promise<UserResponse> {
  const token = getAccessToken();
  if (!token) throw new Error("Giriş yapılmamış");

  const res = await fetch(`${API_BASE}/auth/me`, {
    headers: { Authorization: `Bearer ${token}` },
  });

  if (!res.ok) throw new Error("Kullanıcı bilgisi alınamadı");
  return res.json();
}

export function getAccessToken(): string | null {
  if (typeof window === "undefined") return null;
  return localStorage.getItem(TOKEN_KEY);
}

export function isLoggedIn(): boolean {
  return !!getAccessToken();
}

export function clearTokens(): void {
  if (typeof window === "undefined") return;
  localStorage.removeItem(TOKEN_KEY);
  localStorage.removeItem(REFRESH_KEY);
}
