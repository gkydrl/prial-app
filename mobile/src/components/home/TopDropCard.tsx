import { View, Text, TouchableOpacity } from 'react-native';
import { Image } from 'expo-image';
import { Ionicons } from '@expo/vector-icons';
import { router } from 'expo-router';
import { DiscountBadge } from '@/components/ui/DiscountBadge';
import { useAuthStore } from '@/store/authStore';
import { openAlarmSheet } from '@/store/alarmSheetStore';
import { showAlert } from '@/store/alertStore';

import type { TopDropResponse } from '@/types/api';
import { imageSource } from '@/utils/imageSource';

function capitalize(str: string): string {
  return str
    .split(' ')
    .map((w) => w.charAt(0).toUpperCase() + w.slice(1).toLowerCase())
    .join(' ');
}

function nameFromUrl(url: string): string {
  try {
    const segments = new URL(url).pathname.split('/').filter(Boolean);
    const slug = segments.sort((a, b) => b.length - a.length)[0] ?? '';
    const cleaned = slug
      .replace(/-p-\d+$/, '')
      .replace(/-hb-\d+$/, '')
      .replace(/-\d+$/, '')
      .replace(/-/g, ' ')
      .trim();
    if (!cleaned) return 'Ürün';
    return cleaned
      .split(' ')
      .map((w) => w.charAt(0).toUpperCase() + w.slice(1))
      .join(' ')
      .slice(0, 42);
  } catch {
    return 'Ürün';
  }
}

export function TopDropCard({ item, width = 160, badge = 'both' }: { item: TopDropResponse; width?: number; badge?: 'percent' | 'amount' | 'both' }) {
  const { product, store, price_now, price_24h_ago, drop_percent, drop_amount } = item;
  const isAuthenticated = useAuthStore((s) => s.isAuthenticated);

  const handleAlarmPress = () => {
    if (!isAuthenticated) {
      showAlert('Giriş Gerekli', 'Talep oluşturmak için giriş yapmalısınız.', [
        { text: 'Vazgeç', style: 'cancel' },
        { text: 'Giriş Yap', onPress: () => router.push('/(auth)/login') },
      ]);
      return;
    }
    openAlarmSheet({
      productId: product?.id ?? '',
      storeUrl: store?.url ?? null,
      currentPrice: price_now,
    });
  };

  if (price_now == null) return null;

  const nowStr = price_now.toLocaleString('tr-TR', { maximumFractionDigits: 0 }) + ' ₺';
  const dropAmountStr = drop_amount != null
    ? drop_amount.toLocaleString('tr-TR', { maximumFractionDigits: 0 }) + ' ₺'
    : null;
  const agoStr = price_24h_ago != null
    ? price_24h_ago.toLocaleString('tr-TR', { maximumFractionDigits: 0 }) + ' ₺'
    : null;
  const productName = product?.title ? capitalize(product.title) : nameFromUrl(store?.url ?? '');

  return (
    <TouchableOpacity
      activeOpacity={0.85}
      onPress={() => product?.id && router.push(`/product/${product.id}`)}
      style={{
        width,
        height: 200,
        backgroundColor: '#1E293B',
        borderRadius: 8,
        overflow: 'hidden',
      }}
    >
      {/* Görsel alanı */}
      <View style={{ width: '100%', height: 140, backgroundColor: '#1E293B', padding: 8 }}>
        <View style={{ flex: 1, backgroundColor: '#FFFFFF', borderRadius: 10, overflow: 'hidden' }}>
          <Image
            source={imageSource(product?.image_url)}
            style={{ width: '100%', height: '100%' }}
            contentFit="contain"
            placeholder={{ blurhash: 'L6PZfSi_.AyE_3t7t7R**0o#DgR4' }}
          />
          {/* Drop badge — sol üst köşe (%) */}
          {(badge === 'percent' || badge === 'both') && <DiscountBadge percent={drop_percent} />}
          {/* ₺ düşüş rozeti — sol üst köşe (amount only) veya sağ üst (both) */}
          {(badge === 'amount' || badge === 'both') && dropAmountStr && (
            <View
              style={{
                position: 'absolute',
                top: 8,
                ...(badge === 'both' ? { right: 8 } : { left: 8 }),
                backgroundColor: '#22C55E',
                borderRadius: 20,
                paddingHorizontal: 8,
                paddingVertical: 4,
              }}
            >
              <Text style={{ color: '#FFFFFF', fontSize: 11, fontFamily: 'Inter_700Bold' }}>
                ↘ -{dropAmountStr}
              </Text>
            </View>
          )}
          {/* Talep oluştur — sağ üst yuvarlak buton (both dışında, sağ üst boşsa) */}
          {badge !== 'both' && (
            <TouchableOpacity
              onPress={handleAlarmPress}
              activeOpacity={0.85}
              style={{
                position: 'absolute', top: 8, right: 8,
                width: 24, height: 24, borderRadius: 12,
                backgroundColor: '#1D4ED8',
                justifyContent: 'center', alignItems: 'center',
              }}
            >
              <Ionicons name="add" size={16} color="#FFFFFF" />
            </TouchableOpacity>
          )}
        </View>
      </View>

      {/* Yazı alanı */}
      <View
        style={{
          height: 60,
          paddingHorizontal: 8,
          paddingVertical: 6,
          justifyContent: 'space-between',
        }}
      >
        <Text
          style={{ color: '#FFFFFF', fontSize: 11, fontFamily: 'Inter_600SemiBold', lineHeight: 15 }}
          numberOfLines={1}
        >
          {productName}
        </Text>

        <View style={{ flexDirection: 'row', alignItems: 'center', justifyContent: 'space-between' }}>
          <View style={{ flexDirection: 'row', alignItems: 'center', gap: 4 }}>
            {agoStr && (
              <Text
                style={{
                  color: '#6B7280',
                  fontSize: 11,
                  fontFamily: 'Inter_400Regular',
                  textDecorationLine: 'line-through',
                }}
              >
                {agoStr}
              </Text>
            )}
            <Text style={{ color: '#FFFFFF', fontSize: 16, fontFamily: 'Inter_700Bold' }}>
              {nowStr}
            </Text>
          </View>
          {badge === 'both' && (
            <TouchableOpacity onPress={handleAlarmPress} hitSlop={{ top: 8, bottom: 8, left: 8, right: 8 }}>
              <View style={{
                width: 24, height: 24, borderRadius: 12,
                backgroundColor: '#1D4ED8',
                justifyContent: 'center', alignItems: 'center',
              }}>
                <Ionicons name="add" size={16} color="#FFFFFF" />
              </View>
            </TouchableOpacity>
          )}
        </View>
      </View>
    </TouchableOpacity>
  );
}
