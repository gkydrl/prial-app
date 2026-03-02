import { useEffect } from 'react';
import { View, Text, FlatList, TouchableOpacity } from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';
import { router } from 'expo-router';
import { Ionicons } from '@expo/vector-icons';
import { LinearGradient } from 'expo-linear-gradient';
import { useNotificationStore, type StoredNotification } from '@/store/notificationStore';

const BG = '#0A1628';
const CARD_BG = '#1E293B';
const MUTED = '#64748B';

function timeAgo(isoString: string): string {
  const diff = Math.floor((Date.now() - new Date(isoString).getTime()) / 1000);
  if (diff < 60) return 'Az önce';
  if (diff < 3600) return `${Math.floor(diff / 60)} dk önce`;
  if (diff < 86400) return `${Math.floor(diff / 3600)} sa önce`;
  return `${Math.floor(diff / 86400)} gün önce`;
}

function NotificationItem({ item }: { item: StoredNotification }) {
  const handlePress = () => {
    const data = item.data as Record<string, string>;
    if (data?.product_id) {
      router.push(`/product/${data.product_id}`);
    }
  };

  return (
    <TouchableOpacity
      onPress={handlePress}
      activeOpacity={0.75}
      style={{
        flexDirection: 'row',
        alignItems: 'flex-start',
        backgroundColor: item.read ? CARD_BG : '#263348',
        borderRadius: 12,
        padding: 14,
        gap: 12,
        marginBottom: 8,
      }}
    >
      {/* İkon + okunmadı noktası */}
      <View style={{ position: 'relative' }}>
        <View style={{
          width: 40,
          height: 40,
          borderRadius: 20,
          backgroundColor: '#6C47FF20',
          justifyContent: 'center',
          alignItems: 'center',
        }}>
          <Ionicons name="pricetag-outline" size={20} color="#6C47FF" />
        </View>
        {!item.read && (
          <View style={{
            position: 'absolute',
            top: 0,
            right: 0,
            width: 10,
            height: 10,
            borderRadius: 5,
            backgroundColor: '#22C55E',
            borderWidth: 2,
            borderColor: BG,
          }} />
        )}
      </View>

      {/* İçerik */}
      <View style={{ flex: 1, gap: 4 }}>
        {item.title && (
          <Text style={{ color: '#FFFFFF', fontSize: 14, fontFamily: 'Inter_600SemiBold' }}>
            {item.title}
          </Text>
        )}
        {item.body && (
          <Text style={{ color: '#94A3B8', fontSize: 13, fontFamily: 'Inter_400Regular', lineHeight: 18 }}>
            {item.body}
          </Text>
        )}
        <Text style={{ color: MUTED, fontSize: 11, fontFamily: 'Inter_400Regular', marginTop: 2 }}>
          {timeAgo(item.receivedAt)}
        </Text>
      </View>
    </TouchableOpacity>
  );
}

export default function NotificationsScreen() {
  const { notifications, unreadCount, markAllRead, clear } = useNotificationStore();

  // Ekran açılınca tümünü okundu yap
  useEffect(() => {
    const t = setTimeout(() => markAllRead(), 600);
    return () => clearTimeout(t);
  }, []);

  return (
    <SafeAreaView style={{ flex: 1, backgroundColor: BG }} edges={['top']}>
      {/* Header */}
      <View style={{ paddingHorizontal: 16, paddingVertical: 14, flexDirection: 'row', alignItems: 'center', gap: 8 }}>
        <TouchableOpacity onPress={() => router.back()} hitSlop={{ top: 8, bottom: 8, left: 8, right: 8 }}>
          <Ionicons name="arrow-back" size={22} color="#FFFFFF" />
        </TouchableOpacity>

        <LinearGradient
          colors={['#1D4ED8', '#059669']}
          start={{ x: 0, y: 0 }}
          end={{ x: 0, y: 1 }}
          style={{ width: 3, height: 40, borderRadius: 2, marginLeft: 8 }}
        />
        <Text style={{ flex: 1, color: '#FFFFFF', fontSize: 20, fontFamily: 'Inter_700Bold' }}>
          Bildirimler
        </Text>

        {notifications.length > 0 && (
          <TouchableOpacity onPress={clear} hitSlop={{ top: 8, bottom: 8, left: 8, right: 8 }}>
            <Ionicons name="trash-outline" size={20} color={MUTED} />
          </TouchableOpacity>
        )}
      </View>

      {notifications.length === 0 ? (
        <View style={{ flex: 1, justifyContent: 'center', alignItems: 'center', gap: 12 }}>
          <View style={{
            width: 72,
            height: 72,
            borderRadius: 36,
            backgroundColor: '#1E293B',
            justifyContent: 'center',
            alignItems: 'center',
          }}>
            <Ionicons name="notifications-outline" size={32} color={MUTED} />
          </View>
          <Text style={{ color: '#FFFFFF', fontSize: 16, fontFamily: 'Inter_600SemiBold' }}>
            Henüz bildirim yok
          </Text>
          <Text style={{ color: MUTED, fontSize: 13, fontFamily: 'Inter_400Regular', textAlign: 'center', paddingHorizontal: 40 }}>
            Fiyat düşüşleri ve alarm tetiklenmeleri burada görünecek
          </Text>
        </View>
      ) : (
        <FlatList
          data={notifications}
          keyExtractor={(item) => item.id}
          renderItem={({ item }) => <NotificationItem item={item} />}
          showsVerticalScrollIndicator={false}
          contentContainerStyle={{ paddingHorizontal: 16, paddingTop: 8, paddingBottom: 100 }}
        />
      )}
    </SafeAreaView>
  );
}
