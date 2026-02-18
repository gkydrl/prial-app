import { useState, useEffect } from 'react';
import { productsApi } from '@/api/products';
import type { PriceHistoryPoint, ProductResponse } from '@/types/api';

export function useProduct(id: string) {
  const [product, setProduct] = useState<ProductResponse | null>(null);
  const [history, setHistory] = useState<PriceHistoryPoint[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const fetch = async () => {
    setIsLoading(true);
    setError(null);
    try {
      const [prod, hist] = await Promise.all([
        productsApi.getProduct(id),
        productsApi.getPriceHistory(id),
      ]);
      setProduct(prod.data);
      setHistory(hist.data);
    } catch (e: any) {
      setError(e.message ?? 'Ürün yüklenemedi');
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    fetch();
  }, [id]);

  return { product, history, isLoading, error, refresh: fetch };
}
