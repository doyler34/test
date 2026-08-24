'use client';

import { Lock, Trash2, Unlock } from 'lucide-react';
import { useState } from 'react';

import { StatCard } from '@/components/stat-card';
import { Button } from '@/components/ui/button';
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from '@/components/ui/table';
import {
  useCacheEntries,
  useCacheSummary,
  useDeleteCacheEntry,
  useSetCacheProtected,
} from '@/hooks/use-cache';
import { formatBytes, formatDateTime } from '@/lib/utils';

const SORTS = [
  { value: 'newest', label: 'Newest' },
  { value: 'largest', label: 'Largest' },
  { value: 'most_accessed', label: 'Most Accessed' },
  { value: 'least_recently_used', label: 'Least Recently Used' },
] as const;

export default function CachePage() {
  const [sort, setSort] = useState<(typeof SORTS)[number]['value']>('newest');
  const { data: summary } = useCacheSummary();
  const { data: entries, isLoading } = useCacheEntries(sort);
  const setProtected = useSetCacheProtected();
  const deleteEntry = useDeleteCacheEntry();

  return (
    <div className="space-y-4">
      <h1 className="text-xl font-semibold">Cache</h1>

      <div className="grid grid-cols-2 gap-4 lg:grid-cols-4">
        <StatCard
          label="Total Storage"
          value={summary ? formatBytes(summary.total_bytes) : '—'}
        />
        <StatCard
          label="Used"
          value={summary ? formatBytes(summary.used_bytes) : '—'}
        />
        <StatCard
          label="Free"
          value={summary ? formatBytes(summary.free_bytes) : '—'}
        />
        <StatCard label="Files" value={summary?.entry_count ?? '—'} />
      </div>

      <div className="flex items-center gap-2">
        <span className="text-sm text-muted-foreground">Sort:</span>
        {SORTS.map((s) => (
          <Button
            key={s.value}
            size="sm"
            variant={sort === s.value ? 'default' : 'outline'}
            onClick={() => setSort(s.value)}>
            {s.label}
          </Button>
        ))}
      </div>

      <div className="rounded-md border bg-background">
        <Table>
          <TableHeader>
            <TableRow>
              <TableHead>Path</TableHead>
              <TableHead>Size</TableHead>
              <TableHead className="hidden sm:table-cell">Last Accessed</TableHead>
              <TableHead className="hidden md:table-cell">Access Count</TableHead>
              <TableHead className="text-right">Actions</TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            {isLoading && (
              <TableRow>
                <TableCell
                  colSpan={5}
                  className="text-center text-muted-foreground">
                  Loading…
                </TableCell>
              </TableRow>
            )}
            {entries?.length === 0 && (
              <TableRow>
                <TableCell
                  colSpan={5}
                  className="text-center text-muted-foreground">
                  No cached files.
                </TableCell>
              </TableRow>
            )}
            {entries?.map((entry) => (
              <TableRow key={entry.id}>
                <TableCell
                  className="max-w-[140px] truncate font-mono text-xs sm:max-w-[280px]"
                  title={entry.path}>
                  {entry.path}
                </TableCell>
                <TableCell>{formatBytes(entry.size_bytes)}</TableCell>
                <TableCell className="hidden sm:table-cell">
                  {formatDateTime(entry.last_accessed_at)}
                </TableCell>
                <TableCell className="hidden md:table-cell">{entry.access_count}</TableCell>
                <TableCell className="text-right">
                  <div className="flex items-center justify-end gap-1">
                    <Button
                      variant="ghost"
                      size="icon"
                      title={
                        entry.protected ? 'Unprotect' : 'Protect from eviction'
                      }
                      onClick={() =>
                        setProtected.mutate({
                          id: entry.id,
                          protect: !entry.protected,
                        })
                      }
                      disabled={setProtected.isPending}>
                      {entry.protected ? (
                        <Lock className="h-4 w-4 text-amber-500" />
                      ) : (
                        <Unlock className="h-4 w-4" />
                      )}
                    </Button>
                    <Button
                      variant="ghost"
                      size="icon"
                      title="Delete"
                      onClick={() => {
                        if (confirm('Delete this cached file from disk?')) {
                          deleteEntry.mutate(entry.id);
                        }
                      }}
                      disabled={deleteEntry.isPending}>
                      <Trash2 className="h-4 w-4 text-destructive" />
                    </Button>
                  </div>
                </TableCell>
              </TableRow>
            ))}
          </TableBody>
        </Table>
      </div>
    </div>
  );
}
