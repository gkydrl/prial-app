import { TouchableOpacity, Text, View } from 'react-native';
import { Image } from 'expo-image';
import { router } from 'expo-router';
import { Ionicons } from '@expo/vector-icons';
import { DiscountBadge } from '@/components/ui/DiscountBadge';
import type { ProductResponse, ProductStoreResponse } from '@/types/api';

interface ProductCardProps {
  product: ProductResponse;
  store?: ProductStoreResponse;
}

export function ProductCard({ product, store }: ProductCardProps) {
  const activeStore = store ?? product.stores[0];

  const price = activeStore?.current_price;
  const originalPrice = activeStore?.original_price;
  const discount = activeStore?.discount_percent;

  const priceStr = price != null ? price.toLocaleString('tr-TR', { maximumFractionDigits: 0 }) + ' ₺' : '-';
  const originalStr = originalPrice != null ? originalPrice.toLocaleString('tr-TR', { maximumFractionDigits: 0 }) + ' ₺' : null;

  return (
    <TouchableOpacity
      onPress={() => router.push(`/product/${product.id}`)}
      activeOpacity={0.85}
      style={{
        width: 160,
        height: 200,
        backgroundColor: '#1E293B',
        borderRadius: 16,
        overflow: 'hidden',
      }}
    >
      {/* Görsel alanı */}
      <View style={{ width: '100%', height: 140 }}>
        <Image
          source={{ uri: product.image_url ?? undefined }}
          style={{ width: '100%', height: 140 }}
          contentFit="cover"
          placeholder={{ blurhash: 'L6PZfSi_.AyE_3t7t7R**0o#DgR4' }}
        />
        {/* İndirim badge — sol üst köşe */}
        {!!discount && <DiscountBadge percent={discount} />}
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
              <Text
                style={{
                  color: '#6B7280',
                  fontSize: 11,
                  fontFamily: 'Inter_400Regular',
                  textDecorationLine: 'line-through',
                }}
              >
                {originalStr}
              </Text>
            )}
            <Text style={{ color: '#FFFFFF', fontSize: 16, fontFamily: 'Inter_700Bold' }}>
              {priceStr}
            </Text>
          </View>

          <TouchableOpacity
            onPress={(e) => { e.stopPropagation(); }}
            hitSlop={{ top: 8, bottom: 8, left: 8, right: 8 }}
          >
            <Ionicons name="locate-outline" size={16} color="#6C47FF" />
          </TouchableOpacity>
        </View>
      </View>
    </TouchableOpacity>
  );
}
