import { create } from 'zustand';
import { homeApi } from '@/api/home';
import { CACHE_TTL_MS } from '@/constants/config';
import type { ProductResponse, ProductStoreResponse, TopDropResponse } from '@/types/api';

interface HomeState {
  dailyDeals: ProductStoreResponse[];
  topDrops: TopDropResponse[];
  mostAlarmed: ProductResponse[];
  isLoading: boolean;
  error: string | null;
  lastFetchedAt: number | null;

  fetchAll: () => Promise<void>;
  invalidate: () => void;
}

export const useHomeStore = create<HomeState>((set, get) => ({
  dailyDeals: [],
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
    try {
      const [deals, drops, alarmed] = await Promise.all([
        homeApi.dailyDeals(),
        homeApi.topDrops(),
        homeApi.mostAlarmed(),
      ]);
      set({
        dailyDeals: deals.data,
        topDrops: drops.data,
        mostAlarmed: alarmed.data,
        lastFetchedAt: Date.now(),
      });
    } catch (e: any) {
      set({ error: e.message ?? 'Veriler yüklenemedi' });
    } finally {
      set({ isLoading: false });
    }
  },

  invalidate: () => set({ lastFetchedAt: null }),
}));
