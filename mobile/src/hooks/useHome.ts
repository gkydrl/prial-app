import { useEffect } from 'react';
import { useHomeStore } from '@/store/homeStore';

export function useHome() {
  const dailyDeals = useHomeStore((s) => s.dailyDeals);
  const topDrops = useHomeStore((s) => s.topDrops);
  const mostAlarmed = useHomeStore((s) => s.mostAlarmed);
  const isLoading = useHomeStore((s) => s.isLoading);
  const error = useHomeStore((s) => s.error);
  const fetchAll = useHomeStore((s) => s.fetchAll);
  const invalidate = useHomeStore((s) => s.invalidate);

  useEffect(() => {
    fetchAll();
  }, []);

  const refresh = () => {
    invalidate();
    fetchAll();
  };

  return { dailyDeals, topDrops, mostAlarmed, isLoading, error, refresh };
}
