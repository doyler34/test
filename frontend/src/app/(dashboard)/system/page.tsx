'use client';

import { StatCard } from '@/components/stat-card';
import { StatusBadge } from '@/components/status-badge';
import { Badge } from '@/components/ui/badge';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import {
  useAuditLogs,
  useSystemEvents,
  useSystemMetrics,
  useSystemStatus,
} from '@/hooks/use-system';
import { formatBytes, formatDateTime } from '@/lib/utils';

const EVENT_LEVEL_VARIANT = {
  info: 'secondary',
  warning: 'warning',
  error: 'destructive',
} as const;

export default function SystemPage() {
  const { data: status, isLoading: statusLoading } = useSystemStatus();
  const { data: metrics } = useSystemMetrics();
  const { data: events } = useSystemEvents();
  const { data: auditLogs } = useAuditLogs();

  return (
    <div className="space-y-6">
      <div className="flex items-center gap-3">
        <h1 className="text-xl font-semibold">System</h1>
        {status && <StatusBadge status={status.status} />}
      </div>

      <Card>
        <CardHeader>
          <CardTitle className="text-base text-foreground">
            Component Health
          </CardTitle>
        </CardHeader>
        <CardContent>
          {statusLoading && (
            <p className="text-sm text-muted-foreground">Loading…</p>
          )}
          <div className="grid grid-cols-1 gap-3 sm:grid-cols-2 lg:grid-cols-3">
            {status?.components.map((c) => (
              <div
                key={c.name}
                className="flex items-center justify-between rounded-md border p-3">
                <div>
                  <div className="text-sm font-medium capitalize">{c.name}</div>
                  {c.detail && (
                    <div className="text-xs text-muted-foreground">
                      {c.detail}
                    </div>
                  )}
                </div>
                <StatusBadge status={c.status} />
              </div>
            ))}
          </div>
        </CardContent>
      </Card>

      <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-4">
        <StatCard
          label="CPU"
          value={metrics ? `${metrics.cpu_percent.toFixed(1)}%` : '—'}
        />
        <StatCard
          label="Memory"
          value={
            metrics
              ? `${formatBytes(metrics.memory_used_bytes)} / ${formatBytes(metrics.memory_total_bytes)}`
              : '—'
          }
        />
        <StatCard
          label="Network In"
          value={metrics ? `${formatBytes(metrics.network_rx_bytes_s)}/s` : '—'}
        />
        <StatCard
          label="Network Out"
          value={metrics ? `${formatBytes(metrics.network_tx_bytes_s)}/s` : '—'}
        />
      </div>

      <div className="grid grid-cols-1 gap-4 lg:grid-cols-2">
        <Card>
          <CardHeader>
            <CardTitle className="text-base text-foreground">
              System Events
            </CardTitle>
          </CardHeader>
          <CardContent className="space-y-2">
            {events?.length === 0 && (
              <p className="text-sm text-muted-foreground">
                No events recorded.
              </p>
            )}
            {events?.map((e) => (
              <div
                key={e.id}
                className="flex items-start justify-between gap-2 border-b pb-2 text-sm last:border-0">
                <div className="min-w-0">
                  <p className="truncate">{e.message}</p>
                  <p className="text-xs text-muted-foreground">
                    {e.component} · {formatDateTime(e.created_at)}
                  </p>
                </div>
                <Badge variant={EVENT_LEVEL_VARIANT[e.level]}>{e.level}</Badge>
              </div>
            ))}
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle className="text-base text-foreground">
              Audit Log
            </CardTitle>
          </CardHeader>
          <CardContent className="space-y-2">
            {auditLogs?.length === 0 && (
              <p className="text-sm text-muted-foreground">
                No actions recorded.
              </p>
            )}
            {auditLogs?.map((entry) => (
              <div
                key={entry.id}
                className="border-b pb-2 text-sm last:border-0">
                <p>
                  <span className="font-medium">{entry.action}</span>
                  {entry.target_type && (
                    <span className="text-muted-foreground">
                      {' '}
                      · {entry.target_type}
                    </span>
                  )}
                </p>
                <p className="text-xs text-muted-foreground">
                  {formatDateTime(entry.created_at)}
                </p>
              </div>
            ))}
          </CardContent>
        </Card>
      </div>
    </div>
  );
}
