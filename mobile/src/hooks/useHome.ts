import { useState, useEffect, useCallback } from 'react';
import { homeApi } from '@/api/home';
import type { TopDropResponse, ProductResponse } from '@/types/api';

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
    setDailyDeals(deals.status === 'fulfilled' ? deals.value.data : []);
    setTopDrops(drops.status === 'fulfilled' ? drops.value.data : []);
    setMostAlarmed(alarmed.status === 'fulfilled' ? alarmed.value.data.filter((p: ProductResponse) => p.image_url) : []);
    setIsLoading(false);
  }, []);

  useEffect(() => {
    fetchAll();
  }, [fetchAll]);

  const refresh = useCallback(() => {
    fetchAll();
  }, [fetchAll]);

  return { dailyDeals, topDrops, mostAlarmed, isLoading, error, refresh };
}
