import type { LucideIcon } from 'lucide-react';
import {
  Database,
  Download,
  LayoutDashboard,
  Server,
  Users,
} from 'lucide-react';

export interface NavLink {
  href: string;
  label: string;
  icon: LucideIcon;
  adminOnly?: boolean;
}

export const NAV_LINKS: NavLink[] = [
  { href: '/overview', label: 'Overview', icon: LayoutDashboard },
  { href: '/downloads', label: 'Downloads', icon: Download },
  { href: '/cache', label: 'Cache', icon: Database, adminOnly: true },
  { href: '/users', label: 'Users', icon: Users, adminOnly: true },
  { href: '/system', label: 'System', icon: Server, adminOnly: true },
];
