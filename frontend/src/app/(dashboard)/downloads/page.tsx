'use client';

import { Pause, Play, RotateCcw, Trash2 } from 'lucide-react';
import { useState } from 'react';

import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Progress } from '@/components/ui/progress';
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from '@/components/ui/table';
import { StatusBadge } from '@/components/status-badge';
import {
  useCreateJob,
  useDeleteJob,
  useJobs,
  usePauseJob,
  useResumeJob,
  useRetryJob,
} from '@/hooks/use-jobs';
import { ApiError } from '@/lib/api';
import {
  formatBytes,
  formatDateTime,
  formatEta,
  formatSpeed,
} from '@/lib/utils';
import type { ComponentState } from '@/lib/types';
import type { Job, JobStatus } from '@/lib/types';

const STATUS_VARIANT: Record<JobStatus, ComponentState> = {
  queued: 'degraded',
  downloading: 'ok',
  paused: 'degraded',
  processing: 'degraded',
  completed: 'ok',
  failed: 'down',
  cancelled: 'down',
};

function CreateJobForm() {
  const [source, setSource] = useState('');
  const createJob = useCreateJob();

  const onSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!source.trim()) return;
    try {
      await createJob.mutateAsync(source.trim());
      setSource('');
    } catch {
      // surfaced below
    }
  };

  return (
    <form
      onSubmit={(e) => void onSubmit(e)}
      className="flex flex-col gap-2 sm:flex-row">
      <Input
        placeholder="magnet:?xt=urn:btih:..."
        value={source}
        onChange={(e) => setSource(e.target.value)}
        className="flex-1"
      />
      <Button type="submit" disabled={createJob.isPending || !source.trim()}>
        {createJob.isPending ? 'Adding…' : 'Add download'}
      </Button>
      {createJob.isError && (
        <p className="text-sm text-destructive sm:self-center">
          {createJob.error instanceof ApiError
            ? createJob.error.message
            : 'Failed to add job'}
        </p>
      )}
    </form>
  );
}

function JobActions({ job }: { job: Job }) {
  const pause = usePauseJob();
  const resume = useResumeJob();
  const retry = useRetryJob();
  const del = useDeleteJob();

  return (
    <div className="flex items-center gap-1">
      {(job.status === 'queued' || job.status === 'downloading') && (
        <Button
          variant="ghost"
          size="icon"
          title="Pause"
          onClick={() => pause.mutate(job.id)}
          disabled={pause.isPending}>
          <Pause className="h-4 w-4" />
        </Button>
      )}
      {job.status === 'paused' && (
        <Button
          variant="ghost"
          size="icon"
          title="Resume"
          onClick={() => resume.mutate(job.id)}
          disabled={resume.isPending}>
          <Play className="h-4 w-4" />
        </Button>
      )}
      {(job.status === 'failed' || job.status === 'cancelled') && (
        <Button
          variant="ghost"
          size="icon"
          title="Retry"
          onClick={() => retry.mutate(job.id)}
          disabled={retry.isPending}>
          <RotateCcw className="h-4 w-4" />
        </Button>
      )}
      <Button
        variant="ghost"
        size="icon"
        title="Delete"
        onClick={() => {
          if (
            confirm(
              'Delete this job? This cancels the download and removes its record.',
            )
          ) {
            del.mutate(job.id);
          }
        }}
        disabled={del.isPending}>
        <Trash2 className="h-4 w-4 text-destructive" />
      </Button>
    </div>
  );
}

export default function DownloadsPage() {
  const { data: jobs, isLoading } = useJobs();

  return (
    <div className="space-y-4">
      <h1 className="text-xl font-semibold">Downloads</h1>
      <CreateJobForm />

      <div className="rounded-md border bg-background">
        <Table>
          <TableHeader>
            <TableRow>
              <TableHead>Source</TableHead>
              <TableHead>Status</TableHead>
              <TableHead className="w-32">Progress</TableHead>
              <TableHead className="hidden md:table-cell">Speed</TableHead>
              <TableHead className="hidden md:table-cell">ETA</TableHead>
              <TableHead className="hidden sm:table-cell">Size</TableHead>
              <TableHead className="hidden lg:table-cell">Created</TableHead>
              <TableHead className="text-right">Actions</TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            {isLoading && (
              <TableRow>
                <TableCell
                  colSpan={8}
                  className="text-center text-muted-foreground">
                  Loading…
                </TableCell>
              </TableRow>
            )}
            {jobs?.length === 0 && (
              <TableRow>
                <TableCell
                  colSpan={8}
                  className="text-center text-muted-foreground">
                  No downloads yet.
                </TableCell>
              </TableRow>
            )}
            {jobs?.map((job) => (
              <TableRow key={job.id}>
                <TableCell
                  className="max-w-[120px] truncate font-mono text-xs sm:max-w-[240px]"
                  title={job.source}>
                  {job.source}
                </TableCell>
                <TableCell>
                  <StatusBadge status={STATUS_VARIANT[job.status]} />
                  <span className="ml-1 hidden text-xs text-muted-foreground sm:inline">
                    {job.status}
                  </span>
                </TableCell>
                <TableCell>
                  <Progress value={job.progress * 100} />
                </TableCell>
                <TableCell className="hidden md:table-cell">
                  {formatSpeed(job.speed_bytes_s)}
                </TableCell>
                <TableCell className="hidden md:table-cell">
                  {formatEta(job.eta_seconds)}
                </TableCell>
                <TableCell className="hidden sm:table-cell">
                  {job.total_size_bytes
                    ? formatBytes(job.total_size_bytes)
                    : '—'}
                </TableCell>
                <TableCell className="hidden lg:table-cell">
                  {formatDateTime(job.created_at)}
                </TableCell>
                <TableCell className="text-right">
                  <JobActions job={job} />
                </TableCell>
              </TableRow>
            ))}
          </TableBody>
        </Table>
      </div>
    </div>
  );
}
