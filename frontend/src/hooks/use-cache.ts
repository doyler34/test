'use client';

import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';

import { api } from '@/lib/api';
import type { CacheEntry, CacheSummary } from '@/lib/types';

const CACHE_KEY = ['cache'];

export function useCacheEntries(sort: string) {
  return useQuery({
    queryKey: [...CACHE_KEY, sort],
    queryFn: () => api.get<CacheEntry[]>(`/api/cache?sort=${sort}`),
  });
}

export function useCacheSummary() {
  return useQuery({
    queryKey: [...CACHE_KEY, 'summary'],
    queryFn: () => api.get<CacheSummary>('/api/cache/summary'),
    refetchInterval: 10_000,
  });
}

export function useSetCacheProtected() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({ id, protect }: { id: string; protect: boolean }) =>
      api.patch<CacheEntry>(`/api/cache/${id}`, { protected: protect }),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: CACHE_KEY }),
  });
}

export function useDeleteCacheEntry() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (id: string) => api.delete<void>(`/api/cache/${id}`),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: CACHE_KEY }),
  });
}
