import { useEffect } from 'react';
import { Platform } from 'react-native';
import * as Notifications from 'expo-notifications';
import { router } from 'expo-router';
import { registerForPushNotificationsAsync } from '@/utils/notifications';
import { usersApi } from '@/api/users';
import { useAuthStore } from '@/store/authStore';
import { useNotificationStore } from '@/store/notificationStore';

export function useNotifications() {
  const isAuthenticated = useAuthStore((s) => s.isAuthenticated);
  const addNotification = useNotificationStore((s) => s.addNotification);

  useEffect(() => {
    if (!isAuthenticated) return;
    if (Platform.OS === 'web') return;

    // Push token al ve backend'e gönder
    registerForPushNotificationsAsync().then((token) => {
      if (token) {
        usersApi.updateFirebaseToken(token).catch(console.warn);
      }
    });

    // Gelen bildirimi store'a kaydet
    const receivedSub = Notifications.addNotificationReceivedListener((notification) => {
      const { identifier, content } = notification.request;
      addNotification({
        id: identifier,
        title: content.title ?? null,
        body: content.body ?? null,
        data: (content.data ?? {}) as Record<string, unknown>,
        receivedAt: new Date().toISOString(),
      });
    });

    // Bildirime tıklanınca ilgili ekrana git
    const responseSub = Notifications.addNotificationResponseReceivedListener((response) => {
      const data = response.notification.request.content.data as Record<string, string>;
      if (data?.product_id) {
        router.push(`/product/${data.product_id}`);
      } else {
        router.push('/notifications');
      }
    });

    return () => {
      receivedSub.remove();
      responseSub.remove();
    };
  }, [isAuthenticated]);
}
