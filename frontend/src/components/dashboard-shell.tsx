'use client';

import { LogOut, Menu, X } from 'lucide-react';
import Link from 'next/link';
import { usePathname, useRouter } from 'next/navigation';
import { useState } from 'react';

import { NAV_LINKS } from '@/components/nav-links';
import { ModeToggle } from '@/components/theme-toggle';
import { Button } from '@/components/ui/button';
import { useLogout } from '@/hooks/use-auth';
import { cn } from '@/lib/utils';
import type { User } from '@/lib/types';

function NavItems({
  user,
  onNavigate,
}: {
  user: User;
  onNavigate?: () => void;
}) {
  const pathname = usePathname();
  return (
    <nav className="flex flex-col gap-1 p-2">
      {NAV_LINKS.filter((link) => !link.adminOnly || user.role === 'admin').map(
        (link) => {
          const active = pathname?.startsWith(link.href);
          const Icon = link.icon;
          return (
            <Link
              key={link.href}
              href={link.href}
              onClick={onNavigate}
              className={cn(
                'flex items-center gap-3 rounded-md px-3 py-2 text-sm font-medium transition-colors',
                active
                  ? 'bg-secondary text-secondary-foreground'
                  : 'text-muted-foreground hover:bg-secondary/50 hover:text-foreground',
              )}>
              <Icon className="h-4 w-4" />
              {link.label}
            </Link>
          );
        },
      )}
    </nav>
  );
}

export function DashboardShell({
  user,
  children,
}: {
  user: User;
  children: React.ReactNode;
}) {
  const [mobileOpen, setMobileOpen] = useState(false);
  const router = useRouter();
  const logout = useLogout();

  const handleLogout = async () => {
    await logout.mutateAsync();
    router.push('/login');
  };

  return (
    <div className="min-h-screen bg-muted/20">
      <header className="sticky top-0 z-40 flex h-14 items-center gap-3 border-b bg-background px-4">
        <Button
          variant="ghost"
          size="icon"
          className="sm:hidden"
          onClick={() => setMobileOpen(true)}
          aria-label="Open menu">
          <Menu className="h-5 w-5" />
        </Button>
        <span className="font-semibold">Download / Cache</span>
        <div className="ml-auto flex items-center gap-2">
          <ModeToggle />
          <span className="hidden text-sm text-muted-foreground sm:inline">
            {user.username}
          </span>
          <Button
            variant="ghost"
            size="icon"
            onClick={() => void handleLogout()}
            aria-label="Log out">
            <LogOut className="h-4 w-4" />
          </Button>
        </div>
      </header>

      <div className="flex">
        <aside className="sticky top-14 hidden h-[calc(100vh-3.5rem)] w-56 shrink-0 border-r bg-background sm:block">
          <NavItems user={user} />
        </aside>

        {mobileOpen && (
          <div className="fixed inset-0 z-50 sm:hidden">
            <div
              className="absolute inset-0 bg-black/50"
              onClick={() => setMobileOpen(false)}
            />
            <div className="absolute inset-y-0 left-0 w-64 bg-background shadow-lg">
              <div className="flex h-14 items-center justify-between border-b px-4">
                <span className="font-semibold">Menu</span>
                <Button
                  variant="ghost"
                  size="icon"
                  onClick={() => setMobileOpen(false)}
                  aria-label="Close menu">
                  <X className="h-5 w-5" />
                </Button>
              </div>
              <NavItems user={user} onNavigate={() => setMobileOpen(false)} />
            </div>
          </div>
        )}

        <main className="min-w-0 flex-1 p-4 sm:p-6">{children}</main>
      </div>
    </div>
  );
}
