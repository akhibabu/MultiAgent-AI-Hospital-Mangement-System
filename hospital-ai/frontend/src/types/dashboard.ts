export type AnnouncementPriority = 'Low' | 'Normal' | 'High' | 'Emergency';

export type NotificationCategory =
  | 'Appointments'
  | 'Resources'
  | 'Announcements'
  | 'System';

export interface Announcement {
  id: string;
  title: string;
  description: string;
  priority: AnnouncementPriority;
  category: string;
  is_active: boolean;
  created_by: string | null;
  created_at: string;
  updated_at: string;
}

export interface AnnouncementFormValues {
  title: string;
  description: string;
  priority: AnnouncementPriority;
  category: string;
  is_active: boolean;
}

export interface AnnouncementListParams {
  page?: number;
  page_size?: number;
  search?: string;
  priority?: AnnouncementPriority | '';
  active_only?: boolean;
}

export interface AnnouncementListResponse {
  items: Announcement[];
  total: number;
  page: number;
  page_size: number;
  total_pages: number;
}

export interface AppNotification {
  id: string;
  user_id: string | null;
  title: string;
  message: string;
  category: NotificationCategory;
  priority: AnnouncementPriority;
  link: string | null;
  is_read: boolean;
  created_at: string;
}

export interface NotificationListResponse {
  items: AppNotification[];
  total: number;
  unread_count: number;
}

export const ANNOUNCEMENT_PRIORITIES: AnnouncementPriority[] = [
  'Low',
  'Normal',
  'High',
  'Emergency',
];

export const ANNOUNCEMENT_CATEGORIES = [
  'Hospital Notice',
  'Maintenance',
  'Emergency',
  'System',
];

export const EMPTY_ANNOUNCEMENT_FORM: AnnouncementFormValues = {
  title: '',
  description: '',
  priority: 'Normal',
  category: 'Hospital Notice',
  is_active: true,
};

export const PRIORITY_COLORS: Record<AnnouncementPriority, string> = {
  Low: 'bg-slate-500/15 text-slate-700 dark:text-slate-300',
  Normal: 'bg-sky-500/15 text-sky-700 dark:text-sky-300',
  High: 'bg-amber-500/15 text-amber-800 dark:text-amber-300',
  Emergency: 'bg-rose-500/15 text-rose-700 dark:text-rose-300',
};
