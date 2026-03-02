import { useState, useEffect, useCallback } from 'react';
import {
  View,
  Text,
  TextInput,
  FlatList,
  TouchableOpacity,
  ActivityIndicator,
} from 'react-native';
import { Image } from 'expo-image';
import { SafeAreaView } from 'react-native-safe-area-context';
import { router } from 'expo-router';
import { Ionicons } from '@expo/vector-icons';
import client from '@/api/client';
import { ENDPOINTS } from '@/constants/api';
import type { ProductResponse } from '@/types/api';

const BG = '#0A1628';
const CARD_BG = '#1E293B';

function ProductGridCard({ product }: { product: ProductResponse }) {
  const [imgError, setImgError] = useState(false);
  const store = product.stores?.[0];
  const price = store?.current_price;
  const discount = store?.discount_percent;
  const priceStr = price != null
    ? price.toLocaleString('tr-TR', { maximumFractionDigits: 0 }) + ' ₺'
    : '-';

  return (
    <TouchableOpacity
      onPress={() => router.push(`/product/${product.id}`)}
      activeOpacity={0.85}
      style={{
        flex: 1,
        margin: 4,
        backgroundColor: CARD_BG,
        borderRadius: 8,
        overflow: 'hidden',
      }}
    >
      {/* Görsel */}
      <View style={{ width: '100%', aspectRatio: 1 }}>
        {product.image_url && !imgError ? (
          <Image
            source={{ uri: product.image_url }}
            style={{ width: '100%', height: '100%' }}
            contentFit="contain"
            onError={() => setImgError(true)}
          />
        ) : (
          <View style={{ flex: 1, backgroundColor: '#2D3F55', justifyContent: 'center', alignItems: 'center' }}>
            <Ionicons name="cube-outline" size={36} color="#475569" />
          </View>
        )}
        {!!discount && (
          <View style={{
            position: 'absolute', top: 6, left: 6,
            backgroundColor: '#22C55E', borderRadius: 4,
            paddingHorizontal: 5, paddingVertical: 2,
          }}>
            <Text style={{ color: '#fff', fontSize: 10, fontFamily: 'Inter_700Bold' }}>
              -{discount}%
            </Text>
          </View>
        )}
      </View>

      {/* Bilgi */}
      <View style={{ padding: 8, gap: 4 }}>
        <Text
          style={{ color: '#FFFFFF', fontSize: 11, fontFamily: 'Inter_500Medium', lineHeight: 14 }}
          numberOfLines={2}
        >
          {product.title}
        </Text>
        <View style={{ flexDirection: 'row', justifyContent: 'space-between', alignItems: 'center' }}>
          <Text style={{ color: '#FFFFFF', fontSize: 14, fontFamily: 'Inter_700Bold' }}>
            {priceStr}
          </Text>
          <Ionicons name="pricetag-outline" size={13} color="#6C47FF" />
        </View>
      </View>
    </TouchableOpacity>
  );
}

export default function DiscoverScreen() {
  const [query, setQuery] = useState('');
  const [products, setProducts] = useState<ProductResponse[]>([]);
  const [isLoading, setIsLoading] = useState(true);

  const fetchProducts = useCallback(async (q: string) => {
    setIsLoading(true);
    try {
      const endpoint = q.trim()
        ? ENDPOINTS.DISCOVER_SEARCH
        : '/products';
      const params = q.trim()
        ? { q: q.trim(), limit: 50 }
        : { limit: 50 };
      const res = await client.get<ProductResponse[]>(endpoint, { params });
      setProducts(res.data);
    } catch {
      setProducts([]);
    } finally {
      setIsLoading(false);
    }
  }, []);

  // İlk yükleme
  useEffect(() => {
    fetchProducts('');
  }, []);

  // Arama debounce
  useEffect(() => {
    const t = setTimeout(() => fetchProducts(query), 400);
    return () => clearTimeout(t);
  }, [query]);

  return (
    <SafeAreaView style={{ flex: 1, backgroundColor: BG }} edges={['top']}>
      {/* Başlık + Arama */}
      <View style={{ paddingHorizontal: 16, paddingTop: 4, paddingBottom: 12, gap: 10 }}>
        <Text style={{ color: '#FFFFFF', fontSize: 22, fontFamily: 'Inter_700Bold' }}>
          Keşfet
        </Text>
        <View style={{
          flexDirection: 'row',
          alignItems: 'center',
          backgroundColor: '#1E293B',
          borderRadius: 12,
          paddingHorizontal: 12,
          gap: 8,
        }}>
          <Ionicons name="search-outline" size={18} color="#64748B" />
          <TextInput
            value={query}
            onChangeText={setQuery}
            placeholder="Ürün ara..."
            placeholderTextColor="#475569"
            style={{
              flex: 1,
              color: '#FFFFFF',
              fontSize: 14,
              fontFamily: 'Inter_400Regular',
              paddingVertical: 12,
            }}
            autoCapitalize="none"
            returnKeyType="search"
          />
          {query.length > 0 && (
            <TouchableOpacity onPress={() => setQuery('')}>
              <Ionicons name="close-circle" size={18} color="#475569" />
            </TouchableOpacity>
          )}
        </View>
      </View>

      {/* Ürün Grid */}
      {isLoading ? (
        <View style={{ flex: 1, justifyContent: 'center', alignItems: 'center' }}>
          <ActivityIndicator size="large" color="#6C47FF" />
        </View>
      ) : products.length === 0 ? (
        <View style={{ flex: 1, justifyContent: 'center', alignItems: 'center', gap: 8 }}>
          <Ionicons name="search-outline" size={40} color="#334155" />
          <Text style={{ color: '#64748B', fontSize: 14, fontFamily: 'Inter_400Regular' }}>
            {query ? 'Ürün bulunamadı' : 'Henüz ürün yok'}
          </Text>
        </View>
      ) : (
        <FlatList
          data={products}
          keyExtractor={(item) => item.id}
          numColumns={2}
          showsVerticalScrollIndicator={false}
          contentContainerStyle={{ paddingHorizontal: 8, paddingBottom: 100 }}
          renderItem={({ item }) => <ProductGridCard product={item} />}
        />
      )}
    </SafeAreaView>
  );
}
