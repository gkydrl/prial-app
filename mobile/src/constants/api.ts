export const API_BASE_URL = process.env.EXPO_PUBLIC_API_BASE_URL ?? 'http://localhost:8000/api/v1';

export const ENDPOINTS = {
  // Auth
  REGISTER: '/auth/register',
  LOGIN: '/auth/login',
  REFRESH: '/auth/refresh',
  ME: '/auth/me',

  // Users
  USER_ME: '/users/me',
  USER_FIREBASE_TOKEN: '/users/me/firebase-token',

  // Products
  PRODUCT_ADD: '/products/add',
  PRODUCT_DETAIL: (id: string) => `/products/${id}`,
  PRODUCT_HISTORY: (id: string) => `/products/${id}/price-history`,

  // Alarms
  ALARMS: '/alarms/',
  ALARM_DETAIL: (id: string) => `/alarms/${id}`,

  // Home
  HOME_DAILY_DEALS: '/home/daily-deals',
  HOME_TOP_DROPS: '/home/top-drops',
  HOME_MOST_ALARMED: '/home/most-alarmed',

  // Discover
  DISCOVER_CATEGORIES: '/discover/categories',
  DISCOVER_CATEGORY_PRODUCTS: (slug: string) => `/discover/categories/${slug}/products`,
  DISCOVER_SEARCH: '/discover/search',
} as const;
