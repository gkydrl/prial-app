import client from './client';
import { ENDPOINTS } from '@/constants/api';
import type { CategoryResponse, ProductResponse, ProductStoreResponse } from '@/types/api';
import { PAGE_SIZE } from '@/constants/config';

type SortBy = 'discount' | 'price_asc' | 'price_desc' | 'alarm_count';

export const discoverApi = {
  categories: () =>
    client.get<CategoryResponse[]>(ENDPOINTS.DISCOVER_CATEGORIES),

  categoryProducts: (slug: string, page = 1, sort_by: SortBy = 'discount') =>
    client.get<ProductStoreResponse[]>(ENDPOINTS.DISCOVER_CATEGORY_PRODUCTS(slug), {
      params: { page, page_size: PAGE_SIZE, sort_by },
    }),

  search: (q: string, page = 1) =>
    client.get<ProductResponse[]>(ENDPOINTS.DISCOVER_SEARCH, {
      params: { q, page, page_size: PAGE_SIZE },
    }),
};
