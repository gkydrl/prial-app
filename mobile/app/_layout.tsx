import '../global.css';
import { useEffect } from 'react';
import { Text, TextInput } from 'react-native';
import { Stack } from 'expo-router';
import * as SplashScreen from 'expo-splash-screen';
import { useFonts } from 'expo-font';
import { GestureHandlerRootView } from 'react-native-gesture-handler';
import { useAuthStore } from '@/store/authStore';
import { useNotifications } from '@/hooks/useNotifications';
import { AppAlert } from '@/components/ui/AppAlert';
import { GlobalAlarmSheet } from '@/components/product/GlobalAlarmSheet';

SplashScreen.preventAutoHideAsync();

// Tüm Text ve TextInput bileşenlerinde Inter varsayılan font olarak kullanılır
(Text as any).defaultProps = (Text as any).defaultProps ?? {};
(Text as any).defaultProps.style = [{ fontFamily: 'Inter_400Regular' }];
(TextInput as any).defaultProps = (TextInput as any).defaultProps ?? {};
(TextInput as any).defaultProps.style = [{ fontFamily: 'Inter_400Regular' }];

export default function RootLayout() {
  const hydrate = useAuthStore((s) => s.hydrate);
  const isHydrated = useAuthStore((s) => s.isHydrated);

  useNotifications();

  const [fontsLoaded] = useFonts({
    Inter_400Regular: require('../assets/fonts/Inter_400Regular.ttf'),
    Inter_500Medium: require('../assets/fonts/Inter_500Medium.ttf'),
    Inter_600SemiBold: require('../assets/fonts/Inter_600SemiBold.ttf'),
    Inter_700Bold: require('../assets/fonts/Inter_700Bold.ttf'),
  });

  useEffect(() => {
    hydrate();
  }, []);

  useEffect(() => {
    if (isHydrated && fontsLoaded) {
      SplashScreen.hideAsync();
    }
  }, [isHydrated, fontsLoaded]);

  if (!isHydrated || !fontsLoaded) return null;

  return (
    <GestureHandlerRootView style={{ flex: 1 }}>
      <AppAlert />
      <GlobalAlarmSheet />
      <Stack screenOptions={{ headerShown: false, animation: 'none', contentStyle: { backgroundColor: '#0A1628' } }}>
        <Stack.Screen name="index" />
        <Stack.Screen name="splash" />
        <Stack.Screen name="(auth)" />
        <Stack.Screen name="(tabs)" />
        <Stack.Screen name="product/[id]" options={{ presentation: 'card', animation: 'slide_from_right' }} />
        <Stack.Screen name="discover/category/[slug]" options={{ presentation: 'card', animation: 'slide_from_right' }} />
        <Stack.Screen name="discover/search" options={{ presentation: 'card', animation: 'slide_from_right' }} />
        <Stack.Screen name="notifications" options={{ presentation: 'card', animation: 'slide_from_right' }} />
        <Stack.Screen name="alarm-search" options={{ presentation: 'modal' }} />
        <Stack.Screen name="profile/edit" options={{ presentation: 'card', animation: 'slide_from_right' }} />
        <Stack.Screen name="profile/change-password" options={{ presentation: 'card', animation: 'slide_from_right' }} />
        <Stack.Screen name="profile/about" options={{ presentation: 'card', animation: 'slide_from_right' }} />
        <Stack.Screen name="profile/privacy" options={{ presentation: 'card', animation: 'slide_from_right' }} />
      </Stack>
    </GestureHandlerRootView>
  );
}
