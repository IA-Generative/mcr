export interface Notification {
  id: string;
  title: string;
  content: string;
  type: 'info' | 'warning' | 'error' | 'success';
  read: boolean;
  link?: string;
  timestamp: number;
}

export interface SendNotificationDto {
  recipient_id: string;
  title: string;
  content: string;
  type: 'info' | 'warning' | 'error' | 'success';
  link?: string;
}

export interface UnreadCountResponse {
  unread_count: number;
}
