import client from './client';
import { ENDPOINTS } from '@/constants/api';
import type { ProductResponse, TopDropResponse } from '@/types/api';

export const homeApi = {
  dailyDeals: (limit = 10) =>
    client.get<ProductResponse[]>(ENDPOINTS.HOME_DAILY_DEALS, { params: { limit } }),

  topDrops: (limit = 10) =>
    client.get<TopDropResponse[]>(ENDPOINTS.HOME_TOP_DROPS, { params: { limit } }),

  mostAlarmed: (limit = 10) =>
    client.get<ProductResponse[]>(ENDPOINTS.HOME_MOST_ALARMED, { params: { limit } }),
};
