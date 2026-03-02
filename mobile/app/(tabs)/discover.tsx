import { useState, useEffect, useCallback } from 'react';
import {
  View,
  Text,
  TextInput,
  FlatList,
  TouchableOpacity,
  ActivityIndicator,
  ScrollView,
  Dimensions,
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
const SCREEN_WIDTH = Dimensions.get('window').width;
const CARD_WIDTH = (SCREEN_WIDTH - 32) / 3;

const fmtPrice = (price: number | null) =>
  price != null ? price.toLocaleString('tr-TR') + ' ₺' : '-';

const CATEGORIES: { label: string; slug: string | null; icon: React.ComponentProps<typeof Ionicons>['name'] }[] = [
  { label: 'Tümü', slug: null, icon: 'apps-outline' },
  { label: 'Telefon', slug: 'telefon', icon: 'phone-portrait-outline' },
  { label: 'Bilgisayar', slug: 'bilgisayar', icon: 'laptop-outline' },
  { label: 'Televizyon', slug: 'televizyon', icon: 'tv-outline' },
  { label: 'Ev Aleti', slug: 'ev-aleti', icon: 'home-outline' },
  { label: 'Akıllı Saat', slug: 'akilli-saat', icon: 'watch-outline' },
  { label: 'Oyun', slug: 'oyun-konsolu', icon: 'game-controller-outline' },
  { label: 'Kamera', slug: 'kamera', icon: 'camera-outline' },
  { label: 'Kulaklık', slug: 'kulaklik', icon: 'headset-outline' },
];

function ProductGridCard({ product }: { product: ProductResponse }) {
  const [imgError, setImgError] = useState(false);
  const store = product.stores?.[0];
  const price = store?.current_price;
  const discount = store?.discount_percent;
  const priceStr = fmtPrice(price);

  return (
    <TouchableOpacity
      onPress={() => router.push(`/product/${product.id}`)}
      activeOpacity={0.85}
      style={{
        width: CARD_WIDTH,
        margin: 2,
        backgroundColor: CARD_BG,
        borderRadius: 8,
        overflow: 'hidden',
      }}
    >
      {/* Görsel */}
      <View style={{ width: '100%', height: 100 }}>
        {product.image_url && !imgError ? (
          <Image
            source={{ uri: product.image_url }}
            style={{ width: '100%', height: 100 }}
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
  const [selectedCategory, setSelectedCategory] = useState<string | null>(null);
  const [products, setProducts] = useState<ProductResponse[]>([]);
  const [isLoading, setIsLoading] = useState(true);

  const fetchProducts = useCallback(async (q: string, category: string | null) => {
    setIsLoading(true);
    try {
      if (q.trim()) {
        const res = await client.get<ProductResponse[]>(ENDPOINTS.DISCOVER_SEARCH, {
          params: { q: q.trim(), limit: 50 },
        });
        setProducts(res.data);
      } else {
        const params: Record<string, string | number> = { limit: 50 };
        if (category) params.category = category;
        const res = await client.get<ProductResponse[]>('/products', { params });
        setProducts(res.data);
      }
    } catch {
      setProducts([]);
    } finally {
      setIsLoading(false);
    }
  }, []);

  // İlk yükleme
  useEffect(() => {
    fetchProducts('', null);
  }, []);

  // Arama + kategori debounce
  useEffect(() => {
    const t = setTimeout(() => fetchProducts(query, selectedCategory), 400);
    return () => clearTimeout(t);
  }, [query, selectedCategory]);

  const handleCategoryPress = (slug: string | null) => {
    setSelectedCategory(slug);
    if (query) setQuery('');
  };

  return (
    <SafeAreaView style={{ flex: 1, backgroundColor: BG }} edges={['top']}>
      {/* Başlık + Arama */}
      <View style={{ paddingHorizontal: 16, paddingTop: 4, paddingBottom: 8, gap: 10 }}>
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

      {/* Kategori Chips */}
      <ScrollView
        horizontal
        showsHorizontalScrollIndicator={false}
        contentContainerStyle={{ paddingHorizontal: 12, paddingBottom: 16, gap: 8 }}
      >
        {CATEGORIES.map((cat) => {
          const isActive = selectedCategory === cat.slug;
          return (
            <TouchableOpacity
              key={cat.label}
              onPress={() => handleCategoryPress(cat.slug)}
              activeOpacity={0.75}
              style={{
                width: 52,
                height: 52,
                borderRadius: 26,
                backgroundColor: isActive ? '#6C47FF' : '#1E293B',
                justifyContent: 'center',
                alignItems: 'center',
              }}
            >
              <Ionicons name={cat.icon} size={26} color={isActive ? '#FFFFFF' : '#64748B'} />
            </TouchableOpacity>
          );
        })}
      </ScrollView>

      {/* Ürün Grid */}
      {isLoading ? (
        <View style={{ flex: 1, justifyContent: 'center', alignItems: 'center' }}>
          <ActivityIndicator size="large" color="#6C47FF" />
        </View>
      ) : products.length === 0 ? (
        <View style={{ flex: 1, justifyContent: 'center', alignItems: 'center', gap: 8 }}>
          <Ionicons name="search-outline" size={40} color="#334155" />
          <Text style={{ color: '#64748B', fontSize: 14, fontFamily: 'Inter_400Regular' }}>
            {query ? 'Ürün bulunamadı' : 'Bu kategoride ürün yok'}
          </Text>
        </View>
      ) : (
        <FlatList
          data={products}
          keyExtractor={(item) => item.id}
          numColumns={3}
          showsVerticalScrollIndicator={false}
          contentContainerStyle={{ paddingHorizontal: 8, paddingBottom: 100 }}
          renderItem={({ item }) => <ProductGridCard product={item} />}
        />
      )}
    </SafeAreaView>
  );
}
