import { View, Text, ScrollView, Switch, TouchableOpacity, Alert } from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';
import { router } from 'expo-router';
import { Ionicons } from '@expo/vector-icons';
import { LinearGradient } from 'expo-linear-gradient';
import { useAuth } from '@/hooks/useAuth';
import { usersApi } from '@/api/users';
import Animated from 'react-native-reanimated';
import { useFadeIn } from '@/hooks/useFadeIn';

const BG = '#0A1628';
const ROW_BG = '#0F172A';
const SEPARATOR = '#1E293B';

type IoniconName = React.ComponentProps<typeof Ionicons>['name'];

// ─── Ayar Satırı (ok ile) ─────────────────────────────────────────────────────

function SettingRow({
  icon,
  label,
  onPress,
  showSeparator = true,
}: {
  icon: IoniconName;
  label: string;
  onPress?: () => void;
  showSeparator?: boolean;
}) {
  return (
    <>
      <TouchableOpacity
        onPress={onPress}
        activeOpacity={0.7}
        style={{
          backgroundColor: ROW_BG,
          flexDirection: 'row',
          alignItems: 'center',
          paddingHorizontal: 16,
          paddingVertical: 14,
          gap: 12,
        }}
      >
        <Ionicons name={icon} size={20} color="#64748B" />
        <Text style={{ flex: 1, color: '#FFFFFF', fontSize: 14, fontFamily: 'Inter_400Regular' }}>
          {label}
        </Text>
        <Ionicons name="chevron-forward" size={16} color="#334155" />
      </TouchableOpacity>
      {showSeparator && (
        <View style={{ height: 1, backgroundColor: SEPARATOR, marginLeft: 52 }} />
      )}
    </>
  );
}

// ─── Toggle Satırı ────────────────────────────────────────────────────────────

function ToggleRow({
  icon,
  label,
  value,
  onToggle,
}: {
  icon: IoniconName;
  label: string;
  value: boolean;
  onToggle: (v: boolean) => void;
}) {
  return (
    <View
      style={{
        backgroundColor: ROW_BG,
        flexDirection: 'row',
        alignItems: 'center',
        paddingHorizontal: 16,
        paddingVertical: 10,
        gap: 12,
      }}
    >
      <Ionicons name={icon} size={20} color="#64748B" />
      <Text style={{ flex: 1, color: '#FFFFFF', fontSize: 14, fontFamily: 'Inter_400Regular' }}>
        {label}
      </Text>
      <Switch
        value={value}
        onValueChange={onToggle}
        trackColor={{ false: '#334155', true: '#1D4ED8' }}
        thumbColor="#FFFFFF"
      />
    </View>
  );
}

// ─── Grup Kapsayıcısı ─────────────────────────────────────────────────────────

function SettingGroup({ title, children }: { title: string; children: React.ReactNode }) {
  return (
    <View style={{ gap: 8 }}>
      <Text style={{
        color: '#64748B',
        fontSize: 11,
        fontFamily: 'Inter_600SemiBold',
        textTransform: 'uppercase',
        letterSpacing: 1,
        paddingHorizontal: 4,
      }}>
        {title}
      </Text>
      <View style={{ borderRadius: 16, overflow: 'hidden' }}>
        {children}
      </View>
    </View>
  );
}

// ─── Ana Ekran ────────────────────────────────────────────────────────────────

export default function SettingsScreen() {
  const { user, logout, updateUser } = useAuth();
  const fadeStyle = useFadeIn();

  const handleToggleNotifications = async (value: boolean) => {
    updateUser({ push_notifications_enabled: value });
    try {
      await usersApi.updatePreferences({ push_notifications_enabled: value });
    } catch {
      updateUser({ push_notifications_enabled: !value });
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
    <SafeAreaView style={{ flex: 1, backgroundColor: BG }} edges={['top']}>
      <Animated.View style={[{ flex: 1 }, fadeStyle]}>
      {/* Header */}
      <View style={{ paddingHorizontal: 16, paddingVertical: 14, flexDirection: 'row', alignItems: 'center', gap: 8 }}>
        <LinearGradient
          colors={['#1D4ED8', '#059669']}
          start={{ x: 0, y: 0 }}
          end={{ x: 0, y: 1 }}
          style={{ width: 3, height: 40, borderRadius: 2 }}
        />
        <Text style={{ color: '#FFFFFF', fontSize: 20, fontFamily: 'Inter_700Bold' }}>Ayarlar</Text>
      </View>

      <ScrollView style={{ flex: 1 }} showsVerticalScrollIndicator={false} contentContainerStyle={{ paddingBottom: 40 }}>
        {/* Kullanıcı bilgisi */}
        <View style={{ paddingHorizontal: 20, paddingTop: 4, paddingBottom: 24 }}>
          <Text style={{ color: '#FFFFFF', fontSize: 18, fontFamily: 'Inter_700Bold' }}>
            {user.full_name ?? 'Kullanıcı'}
          </Text>
          <Text style={{ color: '#64748B', fontSize: 13, fontFamily: 'Inter_400Regular', marginTop: 2 }}>
            {user.email}
          </Text>
        </View>

        {/* Gruplar */}
        <View style={{ paddingHorizontal: 16, gap: 0 }}>

          {/* Hesap */}
          <SettingGroup title="Hesap">
            <SettingRow icon="person-outline" label="Profil Bilgileri" onPress={() => {}} />
            <SettingRow icon="lock-closed-outline" label="Şifre Değiştir" onPress={() => {}} showSeparator={false} />
          </SettingGroup>

          {/* Ayraç */}
          <View style={{ height: 1, backgroundColor: SEPARATOR, marginVertical: 20 }} />

          {/* Bildirimler */}
          <SettingGroup title="Bildirimler">
            <ToggleRow
              icon="notifications-outline"
              label="Bildirimler"
              value={user.push_notifications_enabled}
              onToggle={handleToggleNotifications}
            />
          </SettingGroup>

          {/* Ayraç */}
          <View style={{ height: 1, backgroundColor: SEPARATOR, marginVertical: 20 }} />

          {/* Uygulama */}
          <SettingGroup title="Uygulama">
            <SettingRow icon="star-outline" label="Uygulamayı Puanla" onPress={() => {}} />
            <SettingRow icon="share-outline" label="Arkadaşına Öner" onPress={() => {}} />
            <SettingRow icon="document-text-outline" label="Gizlilik Politikası" onPress={() => {}} />
            <SettingRow icon="information-circle-outline" label="Hakkında" onPress={() => {}} showSeparator={false} />
          </SettingGroup>

          {/* Çıkış Yap */}
          <TouchableOpacity
            onPress={handleLogout}
            activeOpacity={0.8}
            style={{
              marginTop: 28,
              backgroundColor: '#EF444415',
              borderWidth: 1,
              borderColor: '#EF444430',
              borderRadius: 16,
              paddingVertical: 16,
              alignItems: 'center',
            }}
          >
            <Text style={{ color: '#EF4444', fontSize: 15, fontFamily: 'Inter_600SemiBold' }}>
              Çıkış Yap
            </Text>
          </TouchableOpacity>

          <View style={{ paddingTop: 20, alignItems: 'center' }}>
            <Text style={{ color: '#334155', fontSize: 11, fontFamily: 'Inter_400Regular' }}>
              Prial v1.0.0
            </Text>
          </View>

        </View>
      </ScrollView>
      </Animated.View>
    </SafeAreaView>
  );
}
