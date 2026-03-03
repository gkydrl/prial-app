import client from './client';
import { ENDPOINTS } from '@/constants/api';
import type { ProductResponse, TopDropResponse } from '@/types/api';

export const homeApi = {
  dailyDeals: (limit = 10, period = '1d') =>
    client.get<TopDropResponse[]>(ENDPOINTS.HOME_DAILY_DEALS, { params: { limit, period } }),

  topDrops: (limit = 10, period = '1d') =>
    client.get<TopDropResponse[]>(ENDPOINTS.HOME_TOP_DROPS, { params: { limit, period } }),

  mostAlarmed: (limit = 10, period?: string) =>
    client.get<ProductResponse[]>(ENDPOINTS.HOME_MOST_ALARMED, {
      params: period ? { limit, period } : { limit },
    }),
};
