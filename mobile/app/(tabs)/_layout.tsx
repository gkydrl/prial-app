import { View, Text, TouchableOpacity } from 'react-native';
import { Redirect, Tabs } from 'expo-router';
import { Ionicons } from '@expo/vector-icons';
import { useSafeAreaInsets } from 'react-native-safe-area-context';
import { useAuthStore } from '@/store/authStore';
import type { BottomTabBarProps } from '@react-navigation/bottom-tabs';

const ACTIVE = '#FFFFFF';
const INACTIVE = '#475569';
const BG = '#0F172A';
const INDICATOR = '#1D4ED8';

const TABS = [
  { name: 'index', title: 'Ana Sayfa', icon: 'home-outline' as const, iconActive: 'home' as const },
  { name: 'discover', title: 'Keşfet', icon: 'compass-outline' as const, iconActive: 'compass' as const },
  { name: 'alarms', title: 'Taleplerim', icon: 'pricetag-outline' as const, iconActive: 'pricetag' as const },
  { name: 'profile', title: 'Ayarlar', icon: 'settings-outline' as const, iconActive: 'settings' as const },
];

function CustomTabBar({ state, navigation }: BottomTabBarProps) {
  const insets = useSafeAreaInsets();

  return (
    <View
      style={{
        backgroundColor: BG,
        borderTopLeftRadius: 20,
        borderTopRightRadius: 20,
        borderTopWidth: 1,
        borderTopColor: '#1E293B',
        paddingTop: 8,
        paddingBottom: insets.bottom > 0 ? insets.bottom : 8,
        paddingHorizontal: 8,
        flexDirection: 'row',
        shadowColor: '#000',
        shadowOffset: { width: 0, height: -4 },
        shadowOpacity: 0.2,
        shadowRadius: 12,
        elevation: 12,
      }}
    >
      {TABS.map((tab, index) => {
        const isFocused = state.index === index;

        return (
          <TouchableOpacity
            key={tab.name}
            onPress={() => navigation.navigate(tab.name)}
            activeOpacity={0.7}
            style={{ flex: 1, alignItems: 'center', gap: 3, paddingVertical: 2 }}
          >
            <Ionicons
              name={isFocused ? tab.iconActive : tab.icon}
              size={22}
              color={isFocused ? INDICATOR : INACTIVE}
            />
            <Text
              style={{
                color: isFocused ? ACTIVE : INACTIVE,
                fontSize: 10,
                fontFamily: isFocused ? 'Inter_600SemiBold' : 'Inter_400Regular',
              }}
            >
              {tab.title}
            </Text>
          </TouchableOpacity>
        );
      })}
    </View>
  );
}

export default function TabsLayout() {
  const isAuthenticated = useAuthStore((s) => s.isAuthenticated);
  const isVerified = useAuthStore((s) => s.user?.is_verified);

  // Redirect authenticated but unverified users to verification screen
  if (isAuthenticated && isVerified === false) {
    return <Redirect href="/(auth)/verify-email" />;
  }

  return (
    <Tabs
      tabBar={(props) => <CustomTabBar {...props} />}
      screenOptions={{ headerShown: false }}
    >
      <Tabs.Screen name="index" options={{ title: 'Ana Sayfa' }} />
      <Tabs.Screen name="discover" options={{ title: 'Keşfet' }} />
      <Tabs.Screen name="alarms" options={{ title: 'Taleplerim' }} />
      <Tabs.Screen name="profile" options={{ title: 'Profil' }} />
    </Tabs>
  );
}
