import apiClient from '@/services/apiClient';
import type {
  DashboardCharts,
  DashboardStatistics,
  GlobalSearchResponse,
  RecentActivities,
  ResourceSummary,
  UpcomingAppointmentItem,
} from '@/types/hospital';

export const dashboardService = {
  async statistics(): Promise<DashboardStatistics> {
    const { data } = await apiClient.get<DashboardStatistics>(
      '/dashboard/statistics',
    );
    return data;
  },
  async charts(): Promise<DashboardCharts> {
    const { data } = await apiClient.get<DashboardCharts>('/dashboard/charts');
    return data;
  },
  async recentActivities(): Promise<RecentActivities> {
    const { data } = await apiClient.get<RecentActivities>(
      '/dashboard/recent-activities',
    );
    return data;
  },
  async upcomingAppointments(): Promise<{
    items: UpcomingAppointmentItem[];
    total: number;
  }> {
    const { data } = await apiClient.get<{
      items: UpcomingAppointmentItem[];
      total: number;
    }>('/dashboard/upcoming-appointments');
    return data;
  },
  async resourceSummary(): Promise<ResourceSummary> {
    const { data } = await apiClient.get<ResourceSummary>(
      '/dashboard/resource-summary',
    );
    return data;
  },
  async search(q: string): Promise<GlobalSearchResponse> {
    const { data } = await apiClient.get<GlobalSearchResponse>('/search', {
      params: { q },
    });
    return data;
  },
};
