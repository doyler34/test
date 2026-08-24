'use client';

import {
  Activity,
  Cpu,
  Database,
  Download,
  HardDrive,
  MemoryStick,
  Users,
} from 'lucide-react';

import { StatCard } from '@/components/stat-card';
import { StatusBadge } from '@/components/status-badge';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { useCurrentUser } from '@/hooks/use-auth';
import { useCacheSummary } from '@/hooks/use-cache';
import { useJobs } from '@/hooks/use-jobs';
import {
  useSystemEvents,
  useSystemMetrics,
  useSystemStatus,
} from '@/hooks/use-system';
import { formatBytes, formatDateTime } from '@/lib/utils';

function formatUptime(seconds: number): string {
  const days = Math.floor(seconds / 86400);
  const hours = Math.floor((seconds % 86400) / 3600);
  const minutes = Math.floor((seconds % 3600) / 60);
  if (days > 0) return `${days}d ${hours}h`;
  if (hours > 0) return `${hours}h ${minutes}m`;
  return `${minutes}m`;
}

function AdminOverview() {
  const { data: status } = useSystemStatus();
  const { data: metrics } = useSystemMetrics();
  const { data: cache } = useCacheSummary();
  const { data: events } = useSystemEvents();
  const recentErrors = events
    ?.filter((e) => e.level === 'error' || e.level === 'warning')
    .slice(0, 5);

  return (
    <div className="space-y-6">
      <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-4">
        <StatCard
          label="Active Downloads"
          value={metrics?.active_downloads ?? '—'}
          icon={Download}
        />
        <StatCard
          label="Active Users"
          value={metrics?.active_users ?? '—'}
          icon={Users}
        />
        <StatCard
          label="Cache Used"
          value={cache ? formatBytes(cache.used_bytes) : '—'}
          icon={Database}
          hint={cache ? `${cache.entry_count} files` : undefined}
        />
        <StatCard
          label="Uptime"
          value={metrics ? formatUptime(metrics.uptime_seconds) : '—'}
          icon={Activity}
        />
      </div>

      <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-4">
        <StatCard
          label="CPU"
          value={metrics ? `${metrics.cpu_percent.toFixed(1)}%` : '—'}
          icon={Cpu}
        />
        <StatCard
          label="Memory"
          value={
            metrics
              ? `${formatBytes(metrics.memory_used_bytes)} / ${formatBytes(metrics.memory_total_bytes)}`
              : '—'
          }
          icon={MemoryStick}
        />
        <StatCard
          label="Network In"
          value={metrics ? `${formatBytes(metrics.network_rx_bytes_s)}/s` : '—'}
          icon={HardDrive}
        />
        <StatCard
          label="Network Out"
          value={metrics ? `${formatBytes(metrics.network_tx_bytes_s)}/s` : '—'}
          icon={HardDrive}
        />
      </div>

      <Card>
        <CardHeader>
          <CardTitle className="text-base text-foreground">
            Component Health
          </CardTitle>
        </CardHeader>
        <CardContent>
          <div className="grid grid-cols-2 gap-3 sm:grid-cols-3 lg:grid-cols-5">
            {status?.components.map((c) => (
              <div
                key={c.name}
                className="flex items-center justify-between rounded-md border p-3">
                <span className="text-sm capitalize">{c.name}</span>
                <StatusBadge status={c.status} />
              </div>
            ))}
          </div>
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle className="text-base text-foreground">
            Recent Errors
          </CardTitle>
        </CardHeader>
        <CardContent className="space-y-2">
          {recentErrors?.length === 0 && (
            <p className="text-sm text-muted-foreground">No recent errors.</p>
          )}
          {recentErrors?.map((e) => (
            <div key={e.id} className="text-sm">
              <span className="text-destructive">{e.component}:</span>{' '}
              {e.message}
              <span className="ml-2 text-xs text-muted-foreground">
                {formatDateTime(e.created_at)}
              </span>
            </div>
          ))}
        </CardContent>
      </Card>
    </div>
  );
}

function UserOverview() {
  const { data: jobs } = useJobs();
  const active = jobs?.filter((j) =>
    ['queued', 'downloading', 'processing'].includes(j.status),
  );

  return (
    <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
      <StatCard
        label="Active Downloads"
        value={active?.length ?? '—'}
        icon={Download}
      />
      <StatCard
        label="Total Jobs"
        value={jobs?.length ?? '—'}
        icon={Activity}
      />
      {jobs && jobs.length > 0 && (
        <Card className="sm:col-span-2">
          <CardHeader>
            <CardTitle className="text-base text-foreground">
              Most Recent Job
            </CardTitle>
          </CardHeader>
          <CardContent className="text-sm text-muted-foreground">
            {jobs[0].source.slice(0, 80)} — created{' '}
            {formatDateTime(jobs[0].created_at)}
          </CardContent>
        </Card>
      )}
    </div>
  );
}

export default function OverviewPage() {
  const { data: user } = useCurrentUser();

  return (
    <div className="space-y-4">
      <h1 className="text-xl font-semibold">Overview</h1>
      {user?.role === 'admin' ? <AdminOverview /> : <UserOverview />}
    </div>
  );
}
