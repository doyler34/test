'use client';

import { useQuery, useQueryClient } from '@tanstack/react-query';

import { api } from '@/lib/api';
import { useEventSource } from '@/hooks/use-sse';
import type {
  AuditLogEntry,
  SystemEvent,
  SystemMetrics,
  SystemStatus,
} from '@/lib/types';

const METRICS_KEY = ['system', 'metrics'];

export function useSystemStatus() {
  return useQuery({
    queryKey: ['system', 'status'],
    queryFn: () => api.get<SystemStatus>('/api/system/status'),
    refetchInterval: 15_000,
  });
}

export function useSystemMetrics() {
  const queryClient = useQueryClient();
  const query = useQuery({
    queryKey: METRICS_KEY,
    queryFn: () => api.get<SystemMetrics>('/api/system/metrics'),
    staleTime: Infinity,
  });

  useEventSource<SystemMetrics>('/api/stream/system', (metrics) => {
    queryClient.setQueryData(METRICS_KEY, metrics);
  });

  return query;
}

export function useSystemEvents() {
  return useQuery({
    queryKey: ['system', 'events'],
    queryFn: () => api.get<SystemEvent[]>('/api/system/events'),
    refetchInterval: 15_000,
  });
}

export function useAuditLogs() {
  return useQuery({
    queryKey: ['system', 'audit-logs'],
    queryFn: () => api.get<AuditLogEntry[]>('/api/system/audit-logs'),
    refetchInterval: 15_000,
  });
}
