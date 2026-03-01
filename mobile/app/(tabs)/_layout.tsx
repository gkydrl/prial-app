import { View, Text, TouchableOpacity } from 'react-native';
import { Redirect, Tabs } from 'expo-router';
import { Ionicons } from '@expo/vector-icons';
import { useAuthStore } from '@/store/authStore';
import type { BottomTabBarProps } from '@react-navigation/bottom-tabs';

const ACTIVE = '#1D4ED8';
const INACTIVE = '#64748B';
const BG = '#0F172A';
const BORDER = '#1E293B';

const TABS = [
  { name: 'index', title: 'Ana Sayfa', icon: 'home' as const },
  { name: 'discover', title: 'Keşfet', icon: 'compass' as const },
  { name: 'alarms', title: 'Taleplerim', icon: 'notifications' as const },
  { name: 'profile', title: 'Ayarlar', icon: 'settings-outline' as const },
];

function CustomTabBar({ state, navigation }: BottomTabBarProps) {
  return (
    <View
      style={{
        flexDirection: 'row',
        backgroundColor: BG,
        borderTopWidth: 1,
        borderTopColor: BORDER,
        paddingBottom: 24,
        paddingTop: 8,
      }}
    >
      {TABS.map((tab, index) => {
        const isFocused = state.index === index;
        const color = isFocused ? ACTIVE : INACTIVE;

        return (
          <TouchableOpacity
            key={tab.name}
            onPress={() => navigation.navigate(tab.name)}
            activeOpacity={0.7}
            style={{ flex: 1, alignItems: 'center', gap: 3 }}
          >
            {/* Aktif sekme üst çizgisi */}
            <View
              style={{
                position: 'absolute',
                top: -8,
                left: 16,
                right: 16,
                height: 2,
                borderRadius: 1,
                backgroundColor: isFocused ? ACTIVE : 'transparent',
              }}
            />
            <Ionicons name={tab.icon} size={22} color={color} />
            <Text style={{ color, fontSize: 10, fontFamily: 'Inter_500Medium' }}>
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

  if (!isAuthenticated) {
    return <Redirect href="/(auth)/login" />;
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
