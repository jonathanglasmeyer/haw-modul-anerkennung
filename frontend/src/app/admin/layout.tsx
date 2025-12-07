'use client';

import { useEffect, useState } from 'react';
import { useRouter, usePathname } from 'next/navigation';
import Link from 'next/link';
import { adminService } from '@/lib/admin-service';

export default function AdminLayout({ children }: { children: React.ReactNode }) {
  const router = useRouter();
  const pathname = usePathname();
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    // Skip auth check on login page
    if (pathname === '/admin/login') {
      setLoading(false);
      return;
    }

    // Check if token exists
    const token = sessionStorage.getItem('admin_token');
    if (!token) {
      router.push('/admin/login');
      return;
    }

    setLoading(false);
  }, [pathname, router]);

  const handleLogout = async () => {
    await adminService.logout();
    router.push('/admin/login');
  };

  // Show loading on auth check
  if (loading) {
    return (
      <>
        <style jsx global>{`
          @import url('https://fonts.googleapis.com/css2?family=IBM+Plex+Mono:wght@400;500&family=IBM+Plex+Sans:wght@400;500;600&display=swap');

          html {
            scrollbar-gutter: stable;
          }

          body {
            font-family: 'IBM Plex Sans', system-ui, -apple-system, sans-serif;
          }
        `}</style>

        <div className="min-h-screen bg-stone-50">
          <header className="bg-white border-b border-stone-200 sticky top-0 z-30 shadow-sm">
            <div className="max-w-7xl mx-auto px-6 py-4">
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-8">
                  <h1 className="text-2xl font-semibold text-stone-900">Admin</h1>
                </div>
              </div>
            </div>
          </header>
          <main className="max-w-7xl mx-auto px-6 py-8">
            <div className="flex items-center justify-center min-h-[400px]">
              <div className="animate-pulse text-stone-500">Loading...</div>
            </div>
          </main>
        </div>
      </>
    );
  }

  // Login page doesn't need nav
  if (pathname === '/admin/login') {
    return <>{children}</>;
  }

  const navItems = [
    { href: '/admin/modules', label: 'Module' },
    { href: '/admin/units', label: 'Units' },
    { href: '/admin/personen', label: 'Personen' },
  ];

  return (
    <>
      <style jsx global>{`
        @import url('https://fonts.googleapis.com/css2?family=IBM+Plex+Mono:wght@400;500&family=IBM+Plex+Sans:wght@400;500;600&display=swap');

        html {
          scrollbar-gutter: stable;
        }

        body {
          font-family: 'IBM Plex Sans', system-ui, -apple-system, sans-serif;
        }
      `}</style>

      <div className="min-h-screen bg-stone-50">
        <header className="bg-white border-b border-stone-200 sticky top-0 z-30 shadow-sm">
          <div className="max-w-7xl mx-auto px-6 py-4">
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-8">
                <h1 className="text-2xl font-semibold text-stone-900">Admin</h1>
                <nav className="flex gap-1">
                  {navItems.map(item => (
                    <Link
                      key={item.href}
                      href={item.href}
                      className={`px-4 py-2 text-sm font-medium rounded-md transition-colors ${
                        pathname === item.href
                          ? 'bg-stone-900 text-white'
                          : 'text-stone-700 hover:text-stone-900 hover:bg-stone-100'
                      }`}
                    >
                      {item.label}
                    </Link>
                  ))}
                </nav>
              </div>
              <div className="flex items-center gap-3">
                <Link
                  href="/"
                  className="px-4 py-2 text-sm font-medium text-stone-700 hover:text-stone-900 hover:bg-stone-100 rounded-md border border-stone-200 transition-colors"
                >
                  Zur Modulanerkennung
                </Link>
                <button
                  onClick={handleLogout}
                  className="px-4 py-2 text-sm font-medium text-stone-700 hover:text-stone-900 hover:bg-stone-100 rounded-md border border-stone-200 transition-colors"
                >
                  Logout
                </button>
              </div>
            </div>
          </div>
        </header>
        <main className="max-w-7xl mx-auto px-6 py-8">
          {children}
        </main>
      </div>
    </>
  );
}
