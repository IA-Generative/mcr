import { reactive, ref } from 'vue';
import type { Notification } from '@/services/notifications/notifications.types';
import {
  getNotifications as fetchNotifications,
  getUnreadCount as fetchUnreadCount,
  markAsRead as apiMarkAsRead,
  markAllAsRead as apiMarkAllAsRead,
} from '@/services/notifications/notifications.service';
import { websocketManager } from '@/services/notifications/websocket-manager';
import useToaster from './use-toaster';

const notifications = reactive<Notification[]>([]);
const unreadCount = ref(0);
const isConnected = ref(false);
const isInitialized = ref(false);

export function useNotifications() {
  const toaster = useToaster();

  async function loadNotifications(): Promise<void> {
    try {
      const data = await fetchNotifications(50);
      notifications.splice(0, notifications.length, ...data);
      await updateUnreadCount();
      isInitialized.value = true;
    } catch (error) {
      console.error('Failed to load notifications:', error);
    }
  }

  async function updateUnreadCount(): Promise<void> {
    try {
      unreadCount.value = await fetchUnreadCount();
    } catch (error) {
      console.error('Failed to fetch unread count:', error);
    }
  }

  function connectWebSocket(token: string): void {
    if (!token) {
      console.warn('Cannot connect WebSocket: no token provided');
      return;
    }

    // Register listener before connecting
    websocketManager.onMessage(handleNewNotification);
    websocketManager.connect(token);
    isConnected.value = true;
  }

  function disconnectWebSocket(): void {
    websocketManager.disconnect();
    isConnected.value = false;
  }

  function handleNewNotification(notification: Notification): void {
    // Add to local state
    notifications.unshift(notification);

    // Update unread count
    if (!notification.read) {
      unreadCount.value++;
    }

    // Show toast notification using existing toaster
    toaster.addMessage({
      title: notification.title,
      description: notification.content,
      type: notification.type,
      closeable: true,
      timeout: 8000, // 8 seconds for notifications
    });

    // Browser notification (if permission granted)
    if (Notification.permission === 'granted') {
      new Notification(notification.title, {
        body: notification.content,
        icon: '/favicon.ico',
      });
    }
  }

  async function markAsRead(notificationId: string): Promise<void> {
    try {
      await apiMarkAsRead(notificationId);

      // Update local state
      const notification = notifications.find(n => n.id === notificationId);
      if (notification && !notification.read) {
        notification.read = true;
        unreadCount.value = Math.max(0, unreadCount.value - 1);
      }
    } catch (error) {
      console.error('Failed to mark notification as read:', error);
    }
  }

  async function markAllAsRead(): Promise<void> {
    try {
      await apiMarkAllAsRead();

      // Update local state
      notifications.forEach(n => n.read = true);
      unreadCount.value = 0;
    } catch (error) {
      console.error('Failed to mark all notifications as read:', error);
    }
  }

  function requestBrowserNotificationPermission(): void {
    if ('Notification' in window && Notification.permission === 'default') {
      Notification.requestPermission();
    }
  }

  return {
    notifications,
    unreadCount,
    isConnected,
    isInitialized,
    loadNotifications,
    connectWebSocket,
    disconnectWebSocket,
    markAsRead,
    markAllAsRead,
    requestBrowserNotificationPermission,
  };
}
