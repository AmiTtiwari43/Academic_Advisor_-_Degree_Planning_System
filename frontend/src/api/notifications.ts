import { apiClient } from './client';

export type NotificationEventType =
  | 'PLAN_SUBMITTED'
  | 'PLAN_UNDER_REVIEW'
  | 'PLAN_APPROVED'
  | 'PLAN_RETURNED'
  | 'PLAN_REJECTED'
  | 'REGISTRATION_REMINDER'
  | 'PREREQUISITE_RISK'
  | 'ADVISOR_QUEUE_SUMMARY';

export type DeliveryStatus = 'PENDING' | 'DELIVERED' | 'FAILED';
export type ReadStatus = 'UNREAD' | 'READ';

export interface NotificationItem {
  id: string;
  institution: string;
  recipient: number;
  event_type: NotificationEventType | string;
  subject: string;
  preview: string;
  payload: Record<string, unknown>;
  delivery_status: DeliveryStatus;
  read_status: ReadStatus;
  read_at: string | null;
  created_at: string;
}

export interface UnreadCountResponse {
  unread_count: number;
}

export interface MarkAllReadResponse {
  updated_count: number;
}

export const notificationsApi = {
  listNotifications: (unreadOnly?: boolean): Promise<NotificationItem[]> => {
    const params: Record<string, string | boolean> = {};
    if (unreadOnly) {
      params.unread_only = true;
    }
    return apiClient.get<NotificationItem[]>('/api/v1/notifications/', { params });
  },

  getUnreadCount: (): Promise<UnreadCountResponse> => {
    return apiClient.get<UnreadCountResponse>('/api/v1/notifications/unread-count/');
  },

  markAsRead: (notificationId: string): Promise<NotificationItem> => {
    return apiClient.post<NotificationItem>(`/api/v1/notifications/${notificationId}/read/`);
  },

  markAllAsRead: (): Promise<MarkAllReadResponse> => {
    return apiClient.post<MarkAllReadResponse>('/api/v1/notifications/read-all/');
  },
};
