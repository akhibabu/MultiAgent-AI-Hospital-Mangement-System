import { useState } from 'react';
import { Outlet, useLocation } from 'react-router-dom';
import Navbar from '@/components/layout/Navbar';
import Sidebar from '@/components/layout/Sidebar';
import { NAV_ITEMS } from '@/utils/constants';

function resolveTitle(pathname: string): string {
  if (pathname.startsWith('/patients/')) return 'Patient Profile';
  if (pathname.startsWith('/doctors/')) return 'Doctor Profile';
  if (pathname === '/appointments/schedule') return 'Doctor Schedule';
  if (pathname.startsWith('/appointments/')) return 'Appointment Details';
  if (pathname.startsWith('/medical-records/files/')) return 'Document Viewer';
  if (pathname.startsWith('/medical-records/')) return 'Medical Record';
  if (pathname.startsWith('/ai/')) return 'AI Agent';
  if (pathname === '/ai') return 'AI Center';
  if (pathname === '/unauthorized') return 'Unauthorized';
  if (pathname === '/server-error') return 'Server Error';
  const match = NAV_ITEMS.find((item) => pathname.startsWith(item.path));
  return match?.label ?? 'Hospital AI';
}

export default function MainLayout() {
  const [sidebarOpen, setSidebarOpen] = useState(false);
  const location = useLocation();
  const title = resolveTitle(location.pathname);

  return (
    <div className="flex min-h-screen bg-[var(--bg-app)]">
      <Sidebar isOpen={sidebarOpen} onClose={() => setSidebarOpen(false)} />
      <div className="flex min-w-0 flex-1 flex-col">
        <Navbar title={title} onMenuClick={() => setSidebarOpen(true)} />
        <main className="flex-1 p-4 lg:p-6">
          <Outlet />
        </main>
      </div>
    </div>
  );
}
