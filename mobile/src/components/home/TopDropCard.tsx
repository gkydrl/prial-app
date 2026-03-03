import { View, Text, TouchableOpacity } from 'react-native';
import { Image } from 'expo-image';
import { Ionicons } from '@expo/vector-icons';
import { router } from 'expo-router';
import { DiscountBadge } from '@/components/ui/DiscountBadge';

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

export function TopDropCard({ item }: { item: TopDropResponse }) {
  const { product, store, price_now, price_24h_ago, drop_percent } = item;

  if (price_now == null) return null;

  const nowStr = price_now.toLocaleString('tr-TR', { maximumFractionDigits: 0 }) + ' ₺';
  const agoStr = price_24h_ago != null
    ? price_24h_ago.toLocaleString('tr-TR', { maximumFractionDigits: 0 }) + ' ₺'
    : null;
  const productName = product?.title ? capitalize(product.title) : nameFromUrl(store?.url ?? '');

  return (
    <TouchableOpacity
      activeOpacity={0.85}
      onPress={() => product?.id && router.push(`/product/${product.id}`)}
      style={{
        width: 160,
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
          {/* Drop badge — sol üst köşe */}
          <DiscountBadge percent={drop_percent} />
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
          <Ionicons name="pricetag-outline" size={14} color="#6C47FF" />
        </View>
      </View>
    </TouchableOpacity>
  );
}
