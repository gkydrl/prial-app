import client from './client';
import { ENDPOINTS } from '@/constants/api';
import type { ProductResponse, ProductStoreResponse, TopDropResponse } from '@/types/api';

export const homeApi = {
  dailyDeals: (limit = 20) =>
    client.get<ProductStoreResponse[]>(ENDPOINTS.HOME_DAILY_DEALS, { params: { limit } }),

  topDrops: (limit = 20) =>
    client.get<TopDropResponse[]>(ENDPOINTS.HOME_TOP_DROPS, { params: { limit } }),

  mostAlarmed: (limit = 20) =>
    client.get<ProductResponse[]>(ENDPOINTS.HOME_MOST_ALARMED, { params: { limit } }),
};
