import { View, Text, ScrollView, Switch, TouchableOpacity, Alert } from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';
import { router } from 'expo-router';
import { useAuth } from '@/hooks/useAuth';
import { usersApi } from '@/api/users';
import { Colors } from '@/constants/colors';
import type { UserUpdatePreferences } from '@/types/api';

function PreferenceRow({
  label,
  value,
  onToggle,
}: {
  label: string;
  value: boolean;
  onToggle: (v: boolean) => void;
}) {
  return (
    <View className="flex-row items-center justify-between py-3.5 border-b border-border">
      <Text className="text-white text-sm">{label}</Text>
      <Switch
        value={value}
        onValueChange={onToggle}
        trackColor={{ false: Colors.border, true: Colors.brand }}
        thumbColor="#fff"
      />
    </View>
  );
}

export default function ProfileScreen() {
  const { user, logout, updateUser } = useAuth();

  const handleToggle = async (field: keyof UserUpdatePreferences, value: boolean) => {
    updateUser({ [field]: value });
    try {
      await usersApi.updatePreferences({ [field]: value });
    } catch {
      // Hata → revert
      updateUser({ [field]: !value });
      Alert.alert('Hata', 'Tercih güncellenemedi');
    }
  };

  const handleLogout = () => {
    Alert.alert('Çıkış Yap', 'Hesabınızdan çıkmak istediğinize emin misiniz?', [
      { text: 'Vazgeç', style: 'cancel' },
      {
        text: 'Çıkış Yap',
        style: 'destructive',
        onPress: () => {
          logout();
          router.replace('/(auth)/login');
        },
      },
    ]);
  };

  if (!user) return null;

  return (
    <SafeAreaView className="flex-1 bg-background" edges={['top']}>
      <ScrollView className="flex-1">
        {/* Kullanıcı bilgisi */}
        <View className="px-4 pt-6 pb-4 items-center gap-2">
          <View className="w-20 h-20 rounded-full bg-brand items-center justify-center">
            <Text className="text-white text-3xl font-bold">
              {(user.full_name ?? user.email)[0].toUpperCase()}
            </Text>
          </View>
          <Text className="text-white text-xl font-bold">{user.full_name ?? 'Kullanıcı'}</Text>
          <Text className="text-muted text-sm">{user.email}</Text>
        </View>

        {/* Bildirim tercihleri */}
        <View className="mx-4 mt-4 bg-card rounded-2xl px-4">
          <Text className="text-muted text-xs font-semibold pt-4 pb-2 uppercase tracking-wider">
            Bildirim Tercihleri
          </Text>
          <PreferenceRow
            label="Push Bildirimleri"
            value={user.push_notifications_enabled}
            onToggle={(v) => handleToggle('push_notifications_enabled', v)}
          />
          <PreferenceRow
            label="E-posta Bildirimleri"
            value={user.email_notifications_enabled}
            onToggle={(v) => handleToggle('email_notifications_enabled', v)}
          />
          <PreferenceRow
            label="Fiyat Düşüşü Bildirimi"
            value={user.notify_on_price_drop}
            onToggle={(v) => handleToggle('notify_on_price_drop', v)}
          />
          <PreferenceRow
            label="Stoğa Girince Bildir"
            value={user.notify_on_back_in_stock}
            onToggle={(v) => handleToggle('notify_on_back_in_stock', v)}
          />
        </View>

        {/* Çıkış */}
        <TouchableOpacity
          className="mx-4 mt-6 bg-danger/10 border border-danger/30 rounded-2xl py-4 items-center"
          onPress={handleLogout}
        >
          <Text className="text-danger font-semibold">Çıkış Yap</Text>
        </TouchableOpacity>

        <View className="py-8 items-center">
          <Text className="text-muted text-xs">Prial v1.0.0</Text>
        </View>
      </ScrollView>
    </SafeAreaView>
  );
}
