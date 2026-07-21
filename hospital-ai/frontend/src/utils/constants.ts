import type { NavItem } from '@/types';

export const APP_NAME =
  import.meta.env.VITE_APP_NAME || 'Hospital AI';

export const NAV_ITEMS: NavItem[] = [
  { label: 'Dashboard', path: '/dashboard' },
  { label: 'Patients', path: '/patients' },
  { label: 'Doctors', path: '/doctors' },
  { label: 'Appointments', path: '/appointments' },
  { label: 'Medical Records', path: '/medical-records' },
  { label: 'Departments', path: '/departments' },
  { label: 'Resources', path: '/resources' },
  { label: 'Profile', path: '/profile' },
];
