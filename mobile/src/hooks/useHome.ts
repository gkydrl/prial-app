import { useState, useEffect, useCallback } from 'react';
import { homeApi } from '@/api/home';
import { getCached, setCache } from '@/utils/apiCache';
import type { TopDropResponse, ProductResponse } from '@/types/api';

const CACHE_KEY = 'cache:home';

interface HomeCacheData {
  dailyDeals: TopDropResponse[];
  topDrops: TopDropResponse[];
  mostAlarmed: ProductResponse[];
}

export function useHome() {
  const [dailyDeals, setDailyDeals] = useState<TopDropResponse[]>([]);
  const [topDrops, setTopDrops] = useState<TopDropResponse[]>([]);
  const [mostAlarmed, setMostAlarmed] = useState<ProductResponse[]>([]);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const fetchAll = useCallback(async () => {
    setIsLoading(true);
    setError(null);
    const [deals, drops, alarmed] = await Promise.allSettled([
      homeApi.dailyDeals(),
      homeApi.topDrops(),
      homeApi.mostAlarmed(),
    ]);
    const dealsData = deals.status === 'fulfilled' ? deals.value.data : [];
    const dropsData = drops.status === 'fulfilled' ? drops.value.data : [];
    const alarmedData = alarmed.status === 'fulfilled'
      ? alarmed.value.data.filter((p: ProductResponse) => p.image_url)
      : [];

    const hasData = dealsData.length > 0 || alarmedData.length > 0;

    if (hasData) {
      setDailyDeals(dealsData);
      setTopDrops(dropsData);
      setMostAlarmed(alarmedData);
      setCache(CACHE_KEY, {
        dailyDeals: dealsData,
        topDrops: dropsData,
        mostAlarmed: alarmedData,
      } as HomeCacheData);
    } else {
      // Tüm istekler başarısız → cache'ten oku
      const cached = await getCached<HomeCacheData>(CACHE_KEY);
      if (cached) {
        setDailyDeals(cached.dailyDeals);
        setTopDrops(cached.topDrops);
        setMostAlarmed(cached.mostAlarmed);
      } else {
        setDailyDeals([]);
        setTopDrops([]);
        setMostAlarmed([]);
      }
    }
    setIsLoading(false);
  }, []);

  useEffect(() => {
    // İlk açılışta: önce cache'ten yükle, sonra API'den güncelle
    (async () => {
      const cached = await getCached<HomeCacheData>(CACHE_KEY);
      if (cached) {
        setDailyDeals(cached.dailyDeals);
        setTopDrops(cached.topDrops);
        setMostAlarmed(cached.mostAlarmed);
      }
      fetchAll();
    })();
  }, [fetchAll]);

  const refresh = useCallback(() => {
    fetchAll();
  }, [fetchAll]);

  return { dailyDeals, topDrops, mostAlarmed, isLoading, error, refresh };
}
