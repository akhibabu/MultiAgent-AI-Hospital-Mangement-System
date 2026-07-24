import apiClient from '@/services/apiClient';
import type {
  Announcement,
  AnnouncementFormValues,
  AnnouncementListParams,
  AnnouncementListResponse,
  AppNotification,
  NotificationListResponse,
} from '@/types/dashboard';

function clean(values: AnnouncementFormValues) {
  return {
    title: values.title.trim(),
    description: values.description.trim(),
    priority: values.priority,
    category: values.category.trim() || 'Hospital Notice',
    is_active: values.is_active,
  };
}

export const announcementService = {
  async list(
    params: AnnouncementListParams = {},
  ): Promise<AnnouncementListResponse> {
    const { data } = await apiClient.get<AnnouncementListResponse>(
      '/announcements',
      {
        params: {
          page: params.page ?? 1,
          page_size: params.page_size ?? 10,
          search: params.search || undefined,
          priority: params.priority || undefined,
          active_only: params.active_only || undefined,
        },
      },
    );
    return data;
  },
  async create(values: AnnouncementFormValues): Promise<Announcement> {
    const { data } = await apiClient.post<Announcement>(
      '/announcements',
      clean(values),
    );
    return data;
  },
  async update(
    id: string,
    values: AnnouncementFormValues,
  ): Promise<Announcement> {
    const { data } = await apiClient.put<Announcement>(
      `/announcements/${id}`,
      clean(values),
    );
    return data;
  },
  async remove(id: string): Promise<void> {
    await apiClient.delete(`/announcements/${id}`);
  },
};

export const notificationService = {
  async list(unreadOnly = false): Promise<NotificationListResponse> {
    const { data } = await apiClient.get<NotificationListResponse>(
      '/notifications',
      { params: { unread_only: unreadOnly || undefined } },
    );
    return data;
  },
  async markRead(id: string): Promise<AppNotification> {
    const { data } = await apiClient.post<AppNotification>(
      `/notifications/${id}/read`,
    );
    return data;
  },
  async markAllRead(): Promise<void> {
    await apiClient.post('/notifications/read-all');
  },
};
