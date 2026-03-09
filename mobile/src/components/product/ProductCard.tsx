import { useState } from 'react';
import { TouchableOpacity, Text, View } from 'react-native';
import { Image } from 'expo-image';
import { router } from 'expo-router';
import { Ionicons } from '@expo/vector-icons';
import { DiscountBadge } from '@/components/ui/DiscountBadge';
import { useAuthStore } from '@/store/authStore';
import { openAlarmSheet } from '@/store/alarmSheetStore';
import { showAlert } from '@/store/alertStore';
import type { ProductResponse, ProductStoreResponse } from '@/types/api';
import { imageSource } from '@/utils/imageSource';

interface ProductCardProps {
  product: ProductResponse;
  store?: ProductStoreResponse;
}

export function ProductCard({ product, store, width = 160 }: ProductCardProps & { width?: number }) {
  const [imgError, setImgError] = useState(false);
  const isAuthenticated = useAuthStore((s) => s.isAuthenticated);
  const activeStore = store ?? product.stores
    .filter(s => s.in_stock)
    .reduce<ProductStoreResponse | undefined>((min, s) => {
      if (!s.current_price) return min;
      if (!min || !min.current_price) return s;
      return Number(s.current_price) < Number(min.current_price) ? s : min;
    }, undefined) ?? product.stores[0];

  const price = activeStore?.current_price;
  const originalPrice = activeStore?.original_price;
  const discount = activeStore?.discount_percent;

  const priceStr = price != null ? price.toLocaleString('tr-TR', { maximumFractionDigits: 0 }) + ' ₺' : '-';
  const originalStr = originalPrice != null ? originalPrice.toLocaleString('tr-TR', { maximumFractionDigits: 0 }) + ' ₺' : null;

  const handleAlarmPress = () => {
    if (!isAuthenticated) {
      showAlert('Giriş Gerekli', 'Talep oluşturmak için giriş yapmalısınız.', [
        { text: 'Vazgeç', style: 'cancel' },
        { text: 'Giriş Yap', onPress: () => router.push('/(auth)/login') },
      ]);
      return;
    }
    openAlarmSheet({
      productId: product.id,
      storeUrl: activeStore?.url ?? null,
      currentPrice: price != null ? Number(price) : null,
    });
  };

  return (
    <TouchableOpacity
      onPress={() => router.push(`/product/${product.id}`)}
      activeOpacity={0.85}
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
          {product.image_url && !imgError ? (
            <Image
              source={imageSource(product.image_url)}
              style={{ width: '100%', height: '100%' }}
              contentFit="contain"
              onError={() => setImgError(true)}
            />
          ) : (
            <View style={{ flex: 1, justifyContent: 'center', alignItems: 'center' }}>
              <Ionicons name="cube-outline" size={40} color="#94A3B8" />
            </View>
          )}
          {/* İndirim badge — sol üst */}
          {!!discount && <DiscountBadge percent={discount} />}

          {/* Talep oluştur — sağ üst yuvarlak buton */}
          <TouchableOpacity
            onPress={handleAlarmPress}
            activeOpacity={0.85}
            style={{
              position: 'absolute', top: 6, right: 6,
              width: 24, height: 24, borderRadius: 12,
              backgroundColor: '#1D4ED8',
              justifyContent: 'center', alignItems: 'center',
            }}
          >
            <Ionicons name="add" size={16} color="#FFFFFF" />
          </TouchableOpacity>
        </View>
      </View>

      {/* Yazı alanı */}
      <View style={{ height: 60, paddingHorizontal: 8, paddingVertical: 6, justifyContent: 'space-between' }}>
        <Text
          style={{ color: '#FFFFFF', fontSize: 11, fontFamily: 'Inter_600SemiBold', lineHeight: 15 }}
          numberOfLines={1}
        >
          {product.title}
        </Text>

        <View style={{ flexDirection: 'row', alignItems: 'center', justifyContent: 'space-between' }}>
          <View style={{ flexDirection: 'row', alignItems: 'center', gap: 4 }}>
            {originalStr && (
              <Text style={{ color: '#6B7280', fontSize: 11, fontFamily: 'Inter_400Regular', textDecorationLine: 'line-through' }}>
                {originalStr}
              </Text>
            )}
            <Text style={{ color: '#FFFFFF', fontSize: 16, fontFamily: 'Inter_700Bold' }}>
              {priceStr}
            </Text>
          </View>

          {/* Talep sayısı — sağ alt */}
          {product.alarm_count > 0 && (
            <View style={{ flexDirection: 'row', alignItems: 'center', gap: 3, backgroundColor: '#1D4ED820', borderRadius: 8, paddingHorizontal: 6, paddingVertical: 3 }}>
              <Ionicons name="pricetag-outline" size={11} color="#93C5FD" />
              <Text style={{ color: '#93C5FD', fontSize: 11, fontFamily: 'Inter_700Bold' }}>
                {product.alarm_count.toLocaleString('tr-TR')} Talep
              </Text>
            </View>
          )}
        </View>
      </View>
    </TouchableOpacity>
  );
}
