import { useEffect } from 'react';
import { Platform } from 'react-native';
import * as Notifications from 'expo-notifications';
import { router } from 'expo-router';
import { registerForPushNotificationsAsync } from '@/utils/notifications';
import { usersApi } from '@/api/users';
import { useAuthStore } from '@/store/authStore';

export function useNotifications() {
  const isAuthenticated = useAuthStore((s) => s.isAuthenticated);

  useEffect(() => {
    if (!isAuthenticated) return;
    if (Platform.OS === 'web') return;

    // Push token al ve backend'e gönder
    registerForPushNotificationsAsync().then((token) => {
      if (token) {
        usersApi.updateFirebaseToken(token).catch(console.warn);
      }
    });

    // Bildirime tıklanınca ürün sayfasına git
    const subscription = Notifications.addNotificationResponseReceivedListener((response) => {
      const data = response.notification.request.content.data as Record<string, string>;
      if (data?.alarm_id) {
        // alarm_id varsa ilgili ürünü aç
        // product_id yoksa alarm listesine yönlendir
        router.push('/(tabs)/alarms');
      }
    });

    return () => subscription.remove();
  }, [isAuthenticated]);
}
