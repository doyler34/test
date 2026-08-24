'use client';

import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';

import { api } from '@/lib/api';
import { useEventSource } from '@/hooks/use-sse';
import type { Job } from '@/lib/types';

const JOBS_KEY = ['jobs'];

export function useJobs() {
  const queryClient = useQueryClient();
  const query = useQuery({
    queryKey: JOBS_KEY,
    queryFn: () => api.get<Job[]>('/api/jobs'),
    staleTime: Infinity, // kept fresh by the SSE subscription below, not refetching
  });

  useEventSource<Job[]>('/api/stream/jobs', (jobs) => {
    queryClient.setQueryData(JOBS_KEY, jobs);
  });

  return query;
}

export function useCreateJob() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (source: string) => api.post<Job>('/api/jobs', { source }),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: JOBS_KEY }),
  });
}

function useJobAction(action: 'pause' | 'resume' | 'retry') {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (id: string) => api.post<Job>(`/api/jobs/${id}/${action}`),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: JOBS_KEY }),
  });
}

export const usePauseJob = () => useJobAction('pause');
export const useResumeJob = () => useJobAction('resume');
export const useRetryJob = () => useJobAction('retry');

export function useDeleteJob() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (id: string) => api.delete<void>(`/api/jobs/${id}`),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: JOBS_KEY }),
  });
}
