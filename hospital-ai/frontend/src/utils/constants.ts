import type { NavItem } from '@/types';

export const APP_NAME =
  import.meta.env.VITE_APP_NAME || 'Hospital';

export const NAV_ITEMS: NavItem[] = [
  { label: 'Dashboard', path: '/dashboard' },
  { label: 'Patients', path: '/patients' },
  { label: 'Doctors', path: '/doctors' },
  { label: 'Departments', path: '/departments' },
  { label: 'Appointments', path: '/appointments' },
  { label: 'Medical Records', path: '/medical-records' },
  { label: 'Resources', path: '/resources' },
  { label: 'Announcements', path: '/announcements' },
  { label: 'AI Center', path: '/ai' },
  { label: 'Validation Center', path: '/validation' },
  { label: 'Availability', path: '/availability' },
  { label: 'Profile', path: '/profile' },
  { label: 'Settings', path: '/settings' },
];
