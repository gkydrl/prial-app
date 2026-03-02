import { View, Text, TouchableOpacity } from 'react-native';
import { Redirect, Tabs } from 'expo-router';
import { Ionicons } from '@expo/vector-icons';
import { useAuthStore } from '@/store/authStore';
import type { BottomTabBarProps } from '@react-navigation/bottom-tabs';

const ACTIVE = '#FFFFFF';
const INACTIVE = '#64748B';
const BG = '#0F172A';

const TABS = [
  { name: 'index', title: 'Ana Sayfa', icon: 'home-outline' as const, iconActive: 'home' as const },
  { name: 'discover', title: 'Keşfet', icon: 'compass-outline' as const, iconActive: 'compass' as const },
  { name: 'alarms', title: 'Taleplerim', icon: 'pricetag-outline' as const, iconActive: 'pricetag' as const },
  { name: 'profile', title: 'Ayarlar', icon: 'settings-outline' as const, iconActive: 'settings' as const },
];

function CustomTabBar({ state, navigation }: BottomTabBarProps) {
  return (
    <View
      style={{
        position: 'absolute',
        bottom: 20,
        left: 20,
        right: 20,
      }}
    >
      <View
        style={{
          flexDirection: 'row',
          backgroundColor: BG,
          borderRadius: 24,
          paddingVertical: 10,
          paddingHorizontal: 8,
          shadowColor: '#000',
          shadowOffset: { width: 0, height: 8 },
          shadowOpacity: 0.4,
          shadowRadius: 16,
          elevation: 12,
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
              style={{ flex: 1, alignItems: 'center', gap: 3, paddingVertical: 4 }}
            >
              <Ionicons
                name={isFocused ? tab.iconActive : tab.icon}
                size={22}
                color={color}
              />
              <Text style={{ color, fontSize: 10, fontFamily: 'Inter_500Medium' }}>
                {tab.title}
              </Text>
            </TouchableOpacity>
          );
        })}
      </View>
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
