import HttpService from '@/services/http/http.service';
import type { Notification, SendNotificationDto, UnreadCountResponse } from './notifications.types';

const NOTIFICATIONS_PATH = 'notifications';

export async function getNotifications(limit = 50): Promise<Notification[]> {
  const response = await HttpService.get<Notification[]>(`/${NOTIFICATIONS_PATH}`, {
    params: { limit },
  });
  return response.data;
}

export async function getUnreadCount(): Promise<number> {
  const response = await HttpService.get<UnreadCountResponse>(
    `/${NOTIFICATIONS_PATH}/unread/count`,
  );
  return response.data.unread_count;
}

export async function sendNotification(dto: SendNotificationDto): Promise<void> {
  await HttpService.post(`/${NOTIFICATIONS_PATH}/send`, dto);
}

export async function markAsRead(notificationId: string): Promise<void> {
  await HttpService.patch(`/${NOTIFICATIONS_PATH}/${notificationId}`);
}

export async function markAllAsRead(): Promise<void> {
  await HttpService.post(`/${NOTIFICATIONS_PATH}/mark-all-read`);
}
