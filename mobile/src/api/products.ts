import client from './client';
import { ENDPOINTS } from '@/constants/api';
import type { AddProductResponse, PriceHistoryPoint, ProductResponse } from '@/types/api';

export const productsApi = {
  add: (url: string, target_price: number) =>
    client.post<AddProductResponse>(ENDPOINTS.PRODUCT_ADD, { url, target_price }),

  getProduct: (id: string) =>
    client.get<ProductResponse>(ENDPOINTS.PRODUCT_DETAIL(id)),

  getPriceHistory: (id: string, store_id?: string) =>
    client.get<PriceHistoryPoint[]>(ENDPOINTS.PRODUCT_HISTORY(id), {
      params: store_id ? { store_id } : undefined,
    }),
};
