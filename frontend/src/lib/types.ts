export type UserRole = 'admin' | 'user';

export interface User {
  id: string;
  username: string;
  email: string;
  role: UserRole;
  is_active: boolean;
  storage_limit_bytes: number | null;
  created_at: string;
  last_login_at: string | null;
}

export type JobStatus =
  | 'queued'
  | 'downloading'
  | 'paused'
  | 'processing'
  | 'completed'
  | 'failed'
  | 'cancelled';

export interface JobFile {
  id: string;
  relative_path: string;
  size_bytes: number;
  mime_type: string | null;
}

export interface Job {
  id: string;
  user_id: string;
  provider: string;
  source: string;
  status: JobStatus;
  progress: number;
  total_size_bytes: number | null;
  downloaded_size_bytes: number;
  speed_bytes_s: number;
  eta_seconds: number | null;
  error_message: string | null;
  created_at: string;
  started_at: string | null;
  completed_at: string | null;
  files: JobFile[];
}

export type CacheEntryStatus = 'active' | 'evicted';

export interface CacheEntry {
  id: string;
  job_id: string | null;
  owner_user_id: string | null;
  path: string;
  size_bytes: number;
  content_hash: string | null;
  created_at: string;
  last_accessed_at: string;
  access_count: number;
  protected: boolean;
  status: CacheEntryStatus;
}

export interface CacheSummary {
  total_bytes: number;
  used_bytes: number;
  free_bytes: number;
  entry_count: number;
}

export interface ApiKey {
  id: string;
  name: string;
  prefix: string;
  created_at: string;
  last_used_at: string | null;
  revoked_at: string | null;
}

export interface ApiKeyCreated extends ApiKey {
  key: string;
}

export type ComponentState = 'ok' | 'degraded' | 'down';

export interface ComponentStatus {
  name: string;
  status: ComponentState;
  detail: string | null;
}

export interface SystemStatus {
  status: ComponentState;
  components: ComponentStatus[];
}

export interface SystemMetrics {
  cpu_percent: number;
  memory_used_bytes: number;
  memory_total_bytes: number;
  network_rx_bytes_s: number;
  network_tx_bytes_s: number;
  active_downloads: number;
  active_users: number;
  cache_used_bytes: number;
  uptime_seconds: number;
}

export interface SystemEvent {
  id: string;
  level: 'info' | 'warning' | 'error';
  component: string;
  message: string;
  meta: Record<string, unknown> | null;
  created_at: string;
}

export interface AuditLogEntry {
  id: string;
  actor_user_id: string | null;
  action: string;
  target_type: string | null;
  target_id: string | null;
  details: Record<string, unknown> | null;
  ip_address: string | null;
  created_at: string;
}
