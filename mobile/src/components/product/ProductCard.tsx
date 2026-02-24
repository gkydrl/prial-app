import { TouchableOpacity, Text, View } from 'react-native';
import { Image } from 'expo-image';
import { router } from 'expo-router';
import { Ionicons } from '@expo/vector-icons';
import type { ProductResponse, ProductStoreResponse } from '@/types/api';

interface ProductCardProps {
  product: ProductResponse;
  store?: ProductStoreResponse;
}

export function ProductCard({ product, store }: ProductCardProps) {
  const activeStore = store ?? product.stores[0];

  const price = activeStore?.current_price;
  const priceStr = price != null ? price.toLocaleString('tr-TR', { maximumFractionDigits: 0 }) + ' ₺' : '-';

  return (
    <TouchableOpacity
      onPress={() => router.push(`/product/${product.id}`)}
      activeOpacity={0.85}
      style={{
        width: 160,
        height: 220,
        backgroundColor: '#0F172A',
        borderRadius: 12,
        overflow: 'hidden',
      }}
    >
      <Image
        source={{ uri: product.image_url ?? undefined }}
        style={{ width: '100%', height: 130 }}
        contentFit="cover"
        placeholder={{ blurhash: 'L6PZfSi_.AyE_3t7t7R**0o#DgR4' }}
      />

      <View style={{ flex: 1, padding: 8 }}>
        <Text
          style={{
            color: '#FFFFFF',
            fontSize: 12,
            fontFamily: 'Inter_600SemiBold',
            lineHeight: 16,
            marginBottom: 4,
          }}
          numberOfLines={2}
        >
          {product.title}
        </Text>

        <View style={{ flexDirection: 'row', alignItems: 'center', justifyContent: 'space-between' }}>
          <View style={{ flexDirection: 'row', alignItems: 'center', gap: 6 }}>
            {!!activeStore?.discount_percent && (
              <View
                style={{
                  backgroundColor: '#22C55E',
                  borderRadius: 4,
                  paddingHorizontal: 5,
                  paddingVertical: 2,
                }}
              >
                <Text style={{ color: '#FFFFFF', fontSize: 10, fontFamily: 'Inter_700Bold' }}>
                  %{activeStore.discount_percent}
                </Text>
              </View>
            )}
            <Text style={{ color: '#FFFFFF', fontSize: 14, fontFamily: 'Inter_700Bold' }}>
              {priceStr}
            </Text>
          </View>

          <TouchableOpacity
            onPress={() => router.push(`/product/${product.id}`)}
            hitSlop={{ top: 8, bottom: 8, left: 8, right: 8 }}
          >
            <Ionicons name="notifications-outline" size={16} color="#6C47FF" />
          </TouchableOpacity>
        </View>
      </View>
    </TouchableOpacity>
  );
}
