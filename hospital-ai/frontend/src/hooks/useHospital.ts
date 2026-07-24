import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { toast } from 'sonner';
import { isAxiosError } from 'axios';
import { resourceService } from '@/services/resourceService';
import type { ResourceFormValues, ResourceListParams } from '@/types/resource';
import {
  announcementService,
  notificationService,
} from '@/services/announcementService';
import type {
  AnnouncementFormValues,
  AnnouncementListParams,
} from '@/types/dashboard';
import { dashboardService } from '@/services/dashboardService';

function errMsg(error: unknown, fallback: string): string {
  if (isAxiosError(error)) {
    const detail = error.response?.data?.detail;
    if (typeof detail === 'string') return detail;
  }
  if (error instanceof Error) return error.message;
  return fallback;
}

export const resourceKeys = {
  all: ['resources'] as const,
  list: (p: ResourceListParams) => [...resourceKeys.all, 'list', p] as const,
};

export const announcementKeys = {
  all: ['announcements'] as const,
  list: (p: AnnouncementListParams) =>
    [...announcementKeys.all, 'list', p] as const,
};

export const notificationKeys = {
  all: ['notifications'] as const,
  list: () => [...notificationKeys.all, 'list'] as const,
};

export const dashboardKeys = {
  all: ['dashboard'] as const,
  stats: () => [...dashboardKeys.all, 'stats'] as const,
  charts: () => [...dashboardKeys.all, 'charts'] as const,
  activities: () => [...dashboardKeys.all, 'activities'] as const,
  upcoming: () => [...dashboardKeys.all, 'upcoming'] as const,
  resources: () => [...dashboardKeys.all, 'resources'] as const,
  search: (q: string) => [...dashboardKeys.all, 'search', q] as const,
};

export function useResources(params: ResourceListParams) {
  return useQuery({
    queryKey: resourceKeys.list(params),
    queryFn: () => resourceService.list(params),
    placeholderData: (p) => p,
  });
}

export function useCreateResource() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (v: ResourceFormValues) => resourceService.create(v),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: resourceKeys.all });
      qc.invalidateQueries({ queryKey: dashboardKeys.all });
      toast.success('Resource added');
    },
    onError: (e) => toast.error(errMsg(e, 'Failed to add resource')),
  });
}

export function useUpdateResource(id: string) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (v: ResourceFormValues) => resourceService.update(id, v),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: resourceKeys.all });
      qc.invalidateQueries({ queryKey: dashboardKeys.all });
      toast.success('Resource updated');
    },
    onError: (e) => toast.error(errMsg(e, 'Failed to update resource')),
  });
}

export function useDeleteResource() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (id: string) => resourceService.remove(id),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: resourceKeys.all });
      qc.invalidateQueries({ queryKey: dashboardKeys.all });
      toast.success('Resource deleted');
    },
    onError: (e) => toast.error(errMsg(e, 'Failed to delete resource')),
  });
}

export function useAnnouncements(params: AnnouncementListParams) {
  return useQuery({
    queryKey: announcementKeys.list(params),
    queryFn: () => announcementService.list(params),
    placeholderData: (p) => p,
  });
}

export function useCreateAnnouncement() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (v: AnnouncementFormValues) => announcementService.create(v),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: announcementKeys.all });
      qc.invalidateQueries({ queryKey: notificationKeys.all });
      toast.success('Announcement published');
    },
    onError: (e) => toast.error(errMsg(e, 'Failed to create announcement')),
  });
}

export function useUpdateAnnouncement(id: string) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (v: AnnouncementFormValues) =>
      announcementService.update(id, v),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: announcementKeys.all });
      toast.success('Announcement updated');
    },
    onError: (e) => toast.error(errMsg(e, 'Failed to update announcement')),
  });
}

export function useDeleteAnnouncement() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (id: string) => announcementService.remove(id),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: announcementKeys.all });
      toast.success('Announcement deleted');
    },
    onError: (e) => toast.error(errMsg(e, 'Failed to delete announcement')),
  });
}

export function useNotifications() {
  return useQuery({
    queryKey: notificationKeys.list(),
    queryFn: () => notificationService.list(),
    refetchInterval: 60_000,
  });
}

export function useMarkNotificationRead() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (id: string) => notificationService.markRead(id),
    onSuccess: () =>
      qc.invalidateQueries({ queryKey: notificationKeys.all }),
  });
}

export function useMarkAllNotificationsRead() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: () => notificationService.markAllRead(),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: notificationKeys.all });
      toast.success('All notifications marked as read');
    },
  });
}

export function useDashboardStatistics() {
  return useQuery({
    queryKey: dashboardKeys.stats(),
    queryFn: () => dashboardService.statistics(),
    staleTime: 30_000,
  });
}

export function useDashboardCharts() {
  return useQuery({
    queryKey: dashboardKeys.charts(),
    queryFn: () => dashboardService.charts(),
    staleTime: 60_000,
  });
}

export function useRecentActivities() {
  return useQuery({
    queryKey: dashboardKeys.activities(),
    queryFn: () => dashboardService.recentActivities(),
    staleTime: 30_000,
  });
}

export function useUpcomingDashboardAppointments() {
  return useQuery({
    queryKey: dashboardKeys.upcoming(),
    queryFn: () => dashboardService.upcomingAppointments(),
    staleTime: 30_000,
  });
}

export function useDashboardResourceSummary() {
  return useQuery({
    queryKey: dashboardKeys.resources(),
    queryFn: () => dashboardService.resourceSummary(),
    staleTime: 30_000,
  });
}

export function useGlobalSearch(q: string) {
  return useQuery({
    queryKey: dashboardKeys.search(q),
    queryFn: () => dashboardService.search(q),
    enabled: q.trim().length >= 2,
    staleTime: 15_000,
  });
}
