'use client';

import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';

import { api } from '@/lib/api';
import type { ApiKey, ApiKeyCreated } from '@/lib/types';

const KEYS_KEY = ['api-keys'];

export function useApiKeys() {
  return useQuery({
    queryKey: KEYS_KEY,
    queryFn: () => api.get<ApiKey[]>('/api/api-keys'),
  });
}

export function useCreateApiKey() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (name: string) =>
      api.post<ApiKeyCreated>('/api/api-keys', { name }),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: KEYS_KEY }),
  });
}

export function useRevokeApiKey() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (id: string) => api.delete<void>(`/api/api-keys/${id}`),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: KEYS_KEY }),
  });
}
