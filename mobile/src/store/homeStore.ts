import { create } from 'zustand';
import { homeApi } from '@/api/home';
import { CACHE_TTL_MS } from '@/constants/config';
import { getCached, setCache } from '@/utils/apiCache';
import type { ProductResponse, TopDropResponse } from '@/types/api';

const CACHE_KEY = 'cache:home';

interface HomeCacheData {
  dailyDeals: TopDropResponse[];
  topDrops: TopDropResponse[];
  mostAlarmed: ProductResponse[];
}

interface HomeState {
  dailyDeals: TopDropResponse[];
  topDrops: TopDropResponse[];
  mostAlarmed: ProductResponse[];
  isLoading: boolean;
  error: string | null;
  lastFetchedAt: number | null;

  fetchAll: () => Promise<void>;
  invalidate: () => void;
}

export const useHomeStore = create<HomeState>((set, get) => ({
  dailyDeals: [] as TopDropResponse[],
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
    const dailyDeals = deals.status === 'fulfilled' ? deals.value.data : [];
    const topDrops = drops.status === 'fulfilled' ? drops.value.data : [];
    const mostAlarmed = alarmed.status === 'fulfilled' ? alarmed.value.data : [];

    const hasData = dailyDeals.length > 0 || mostAlarmed.length > 0;

    if (hasData) {
      // Başarılı → diske yaz
      setCache(CACHE_KEY, { dailyDeals, topDrops, mostAlarmed } as HomeCacheData);
      set({
        dailyDeals,
        topDrops,
        mostAlarmed,
        lastFetchedAt: Date.now(),
        isLoading: false,
      });
    } else {
      // Tüm istekler başarısız → diskten oku
      const cached = await getCached<HomeCacheData>(CACHE_KEY);
      if (cached) {
        set({
          dailyDeals: cached.dailyDeals,
          topDrops: cached.topDrops,
          mostAlarmed: cached.mostAlarmed,
          lastFetchedAt: null,
          isLoading: false,
        });
      } else {
        set({
          dailyDeals: [],
          topDrops: [],
          mostAlarmed: [],
          lastFetchedAt: null,
          isLoading: false,
        });
      }
    }
  },

  invalidate: () => set({ lastFetchedAt: null }),
}));
