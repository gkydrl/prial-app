import { create } from 'zustand';
import { homeApi } from '@/api/home';
import { CACHE_TTL_MS } from '@/constants/config';
import type { ProductResponse, TopDropResponse } from '@/types/api';

interface HomeState {
  dailyDeals: ProductResponse[];
  topDrops: TopDropResponse[];
  mostAlarmed: ProductResponse[];
  isLoading: boolean;
  error: string | null;
  lastFetchedAt: number | null;

  fetchAll: () => Promise<void>;
  invalidate: () => void;
}

export const useHomeStore = create<HomeState>((set, get) => ({
  dailyDeals: [] as ProductResponse[],
  topDrops: [],
  mostAlarmed: [],
  isLoading: false,
  error: null,
  lastFetchedAt: null,

  fetchAll: async () => {
    const { lastFetchedAt } = get();
    // 5 dakika TTL cache kontrolü
    if (lastFetchedAt && Date.now() - lastFetchedAt < CACHE_TTL_MS) return;

    set({ isLoading: true, error: null });
    const [deals, drops, alarmed] = await Promise.allSettled([
      homeApi.dailyDeals(),
      homeApi.topDrops(),
      homeApi.mostAlarmed(),
    ]);
    set({
      dailyDeals: deals.status === 'fulfilled' ? deals.value.data : [],
      topDrops: drops.status === 'fulfilled' ? drops.value.data : [],
      mostAlarmed: alarmed.status === 'fulfilled' ? alarmed.value.data : [],
      lastFetchedAt: Date.now(),
      isLoading: false,
    });
  },

  invalidate: () => set({ lastFetchedAt: null }),
}));
