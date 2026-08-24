'use client';

import { useRouter } from 'next/navigation';
import { useEffect } from 'react';

import { DashboardShell } from '@/components/dashboard-shell';
import { useCurrentUser } from '@/hooks/use-auth';

export default function DashboardLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  const router = useRouter();
  const { data: user, isLoading, isError } = useCurrentUser();

  useEffect(() => {
    if (isError) {
      router.replace('/login');
    }
  }, [isError, router]);

  if (isLoading) {
    return (
      <div className="flex min-h-screen items-center justify-center text-sm text-muted-foreground">
        Loading…
      </div>
    );
  }

  if (!user) {
    return null;
  }

  return <DashboardShell user={user}>{children}</DashboardShell>;
}
