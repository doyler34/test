import { Badge } from '@/components/ui/badge';
import type { ComponentState } from '@/lib/types';

const VARIANTS: Record<ComponentState, 'success' | 'warning' | 'destructive'> =
  {
    ok: 'success',
    degraded: 'warning',
    down: 'destructive',
  };

const LABELS: Record<ComponentState, string> = {
  ok: 'OK',
  degraded: 'Degraded',
  down: 'Down',
};

export function StatusBadge({ status }: { status: ComponentState }) {
  return <Badge variant={VARIANTS[status]}>{LABELS[status]}</Badge>;
}
