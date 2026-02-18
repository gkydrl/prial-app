import { useState, useEffect, useCallback, useRef } from 'react';
import { discoverApi } from '@/api/discover';
import { DEBOUNCE_MS } from '@/constants/config';
import type { CategoryResponse, ProductResponse, ProductStoreResponse } from '@/types/api';

export function useCategories() {
  const [categories, setCategories] = useState<CategoryResponse[]>([]);
  const [isLoading, setIsLoading] = useState(true);

  useEffect(() => {
    discoverApi.categories().then(({ data }) => {
      setCategories(data);
      setIsLoading(false);
    });
  }, []);

  return { categories, isLoading };
}

export function useCategoryProducts(slug: string) {
  const [products, setProducts] = useState<ProductStoreResponse[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [page, setPage] = useState(1);
  const [hasMore, setHasMore] = useState(true);

  const load = useCallback(
    async (p = 1) => {
      setIsLoading(true);
      try {
        const { data } = await discoverApi.categoryProducts(slug, p);
        if (p === 1) {
          setProducts(data);
        } else {
          setProducts((prev) => [...prev, ...data]);
        }
        setHasMore(data.length === 20);
        setPage(p);
      } finally {
        setIsLoading(false);
      }
    },
    [slug]
  );

  useEffect(() => {
    load(1);
  }, [slug]);

  const loadMore = () => {
    if (hasMore && !isLoading) load(page + 1);
  };

  return { products, isLoading, hasMore, loadMore, refresh: () => load(1) };
}

export function useSearch() {
  const [query, setQuery] = useState('');
  const [results, setResults] = useState<ProductResponse[]>([]);
  const [isLoading, setIsLoading] = useState(false);
  const timerRef = useRef<ReturnType<typeof setTimeout> | null>(null);

  useEffect(() => {
    if (timerRef.current) clearTimeout(timerRef.current);

    if (query.length < 2) {
      setResults([]);
      return;
    }

    timerRef.current = setTimeout(async () => {
      setIsLoading(true);
      try {
        const { data } = await discoverApi.search(query);
        setResults(data);
      } finally {
        setIsLoading(false);
      }
    }, DEBOUNCE_MS);

    return () => {
      if (timerRef.current) clearTimeout(timerRef.current);
    };
  }, [query]);

  return { query, setQuery, results, isLoading };
}
