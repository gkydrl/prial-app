import { useState, useEffect, useCallback, useMemo } from 'react';
import {
  View,
  Text,
  TextInput,
  TouchableOpacity,
  ActivityIndicator,
  ScrollView,
  Dimensions,
} from 'react-native';
import { Image } from 'expo-image';
import { SafeAreaView } from 'react-native-safe-area-context';
import { router } from 'expo-router';
import { Ionicons } from '@expo/vector-icons';
import { LinearGradient } from 'expo-linear-gradient';
import client from '@/api/client';
import { ENDPOINTS } from '@/constants/api';
import type { ProductResponse } from '@/types/api';
import Animated from 'react-native-reanimated';
import { useFadeIn } from '@/hooks/useFadeIn';
import { imageSource } from '@/utils/imageSource';

const BG = '#0A1628';
const CARD_BG = '#1E293B';
const SCREEN_WIDTH = Dimensions.get('window').width;
// Container: SCREEN_WIDTH - 16 (paddingHorizontal: 8 her iki taraf)
// 3 kart × (margin-left 2 + margin-right 2) = 12px kenar boşluğu
// CARD_WIDTH = (SCREEN_WIDTH - 16 - 12) / 3
const CARD_WIDTH = (SCREEN_WIDTH - 28) / 3;

// Her 6 üründe 1 öne çıkan blok: 1 büyük + 2 yan + 3 alt
const FEATURED_INTERVAL = 6;
// Büyük kart + 2 yan kartın toplam yüksekliği
const FEATURED_ROW_HEIGHT = 270;
// Yan küçük kartlarda görsel için sabit yükseklik
const SIDE_IMAGE_H = 88;

const fmtPrice = (price: number | null) =>
  price != null ? Math.round(price).toLocaleString('tr-TR') + ' ₺' : '-';

const CATEGORIES: { label: string; slug: string | null; icon: React.ComponentProps<typeof Ionicons>['name'] }[] = [
  { label: 'Tümü', slug: null, icon: 'apps' },
  { label: 'Telefon', slug: 'telefon', icon: 'phone-portrait' },
  { label: 'Bilgisayar', slug: 'bilgisayar', icon: 'laptop' },
  { label: 'Televizyon', slug: 'televizyon', icon: 'tv' },
  { label: 'Ev Aleti', slug: 'ev-aleti', icon: 'home' },
  { label: 'Akıllı Saat', slug: 'akilli-saat', icon: 'watch' },
  { label: 'Oyun', slug: 'oyun-konsolu', icon: 'game-controller' },
  { label: 'Kamera', slug: 'kamera', icon: 'camera' },
  { label: 'Kulaklık', slug: 'kulaklik', icon: 'headset' },
];

// ─── Büyük öne çıkan kart (soldaki 2/3) ──────────────────────────────────────

function FeaturedCard({ product }: { product: ProductResponse }) {
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
        flex: 2,
        backgroundColor: CARD_BG,
        borderRadius: 10,
        overflow: 'hidden',
        margin: 2,
      }}
    >
      {/* Görsel */}
      <View style={{ flex: 1 }}>
        {product.image_url && !imgError ? (
          <Image
            source={imageSource(product.image_url)}
            style={{ width: '100%', height: '100%' }}
            contentFit="contain"
            onError={() => setImgError(true)}
          />
        ) : (
          <View style={{ flex: 1, backgroundColor: '#2D3F55', justifyContent: 'center', alignItems: 'center' }}>
            <Ionicons name="cube-outline" size={48} color="#475569" />
          </View>
        )}

        {/* "ÖNE ÇIKAN" badge */}
        <View style={{
          position: 'absolute', top: 8, left: 8,
          backgroundColor: '#6C47FF', borderRadius: 5,
          paddingHorizontal: 7, paddingVertical: 3,
        }}>
          <Text style={{ color: '#fff', fontSize: 9, fontFamily: 'Inter_700Bold', letterSpacing: 0.8 }}>
            ÖNE ÇIKAN
          </Text>
        </View>

        {!!discount && (
          <View style={{
            position: 'absolute', top: 8, right: 8,
            backgroundColor: '#22C55E', borderRadius: 5,
            paddingHorizontal: 7, paddingVertical: 3,
          }}>
            <Text style={{ color: '#fff', fontSize: 10, fontFamily: 'Inter_700Bold' }}>
              -{discount}%
            </Text>
          </View>
        )}
      </View>

      {/* Bilgi */}
      <View style={{ padding: 10, gap: 4 }}>
        <Text
          style={{ color: '#FFFFFF', fontSize: 12, fontFamily: 'Inter_600SemiBold', lineHeight: 16 }}
          numberOfLines={2}
        >
          {product.title}
        </Text>
        <Text style={{ color: '#FFFFFF', fontSize: 16, fontFamily: 'Inter_700Bold' }}>
          {priceStr}
        </Text>
      </View>
    </TouchableOpacity>
  );
}

// ─── Yan küçük kart (sağdaki 1/3, 2 adet dikey) ──────────────────────────────

function SideCard({ product }: { product: ProductResponse }) {
  const [imgError, setImgError] = useState(false);
  const store = product.stores?.[0];
  const price = store?.current_price;
  const priceStr = fmtPrice(price);

  return (
    <TouchableOpacity
      onPress={() => router.push(`/product/${product.id}`)}
      activeOpacity={0.85}
      style={{
        flex: 1,
        backgroundColor: CARD_BG,
        borderRadius: 8,
        overflow: 'hidden',
        minHeight: 0,
      }}
    >
      {/* Sabit yükseklik görsel alanı — gri kutu kartı ele geçirmesin */}
      <View style={{ height: SIDE_IMAGE_H }}>
        {product.image_url && !imgError ? (
          <Image
            source={imageSource(product.image_url)}
            style={{ width: '100%', height: SIDE_IMAGE_H }}
            contentFit="contain"
            onError={() => setImgError(true)}
          />
        ) : (
          <View style={{ flex: 1, backgroundColor: '#2D3F55', justifyContent: 'center', alignItems: 'center' }}>
            <Ionicons name="cube-outline" size={22} color="#475569" />
          </View>
        )}
      </View>

      {/* Yazı — geri kalan alanı doldur */}
      <View style={{ flex: 1, padding: 6, justifyContent: 'center' }}>
        <Text
          style={{ color: '#FFFFFF', fontSize: 10, fontFamily: 'Inter_500Medium', lineHeight: 13 }}
          numberOfLines={2}
        >
          {product.title}
        </Text>
        <Text style={{ color: '#FFFFFF', fontSize: 12, fontFamily: 'Inter_700Bold', marginTop: 3 }}>
          {priceStr}
        </Text>
      </View>
    </TouchableOpacity>
  );
}

// ─── Normal 3'lü grid kartı ────────────────────────────────────────────────────

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
      <View style={{ width: '100%', height: 100 }}>
        {product.image_url && !imgError ? (
          <Image
            source={imageSource(product.image_url)}
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

// ─── Gruplama ─────────────────────────────────────────────────────────────────

type ProductGroup = {
  featured: ProductResponse;
  sideCards: ProductResponse[];   // 2 adet — sağ yan
  belowCards: ProductResponse[];  // 3 adet — alt satır
};

function groupProducts(products: ProductResponse[], interval: number): ProductGroup[] {
  const groups: ProductGroup[] = [];
  let i = 0;
  while (i < products.length) {
    const featured = products[i];
    const sideCards = products.slice(i + 1, i + 3);
    const belowCards = products.slice(i + 3, i + interval);
    groups.push({ featured, sideCards, belowCards });
    i += interval;
  }
  return groups;
}

// ─── Ana Ekran ────────────────────────────────────────────────────────────────

export default function DiscoverScreen() {
  const [query, setQuery] = useState('');
  const [selectedCategory, setSelectedCategory] = useState<string | null>(null);
  const [products, setProducts] = useState<ProductResponse[]>([]);
  const [isLoading, setIsLoading] = useState(true);

  const productGroups = useMemo(() => groupProducts(products, FEATURED_INTERVAL), [products]);
  const fadeStyle = useFadeIn();

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

  useEffect(() => {
    fetchProducts('', null);
  }, []);

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
      <Animated.View style={[{ flex: 1 }, fadeStyle]}>
      {/* Başlık + Arama */}
      <View style={{ paddingHorizontal: 16, paddingTop: 14, paddingBottom: 8, gap: 10 }}>
        <View style={{ flexDirection: 'row', alignItems: 'center', gap: 8 }}>
          <LinearGradient
            colors={['#1D4ED8', '#059669']}
            start={{ x: 0, y: 0 }}
            end={{ x: 0, y: 1 }}
            style={{ width: 3, height: 40, borderRadius: 2 }}
          />
          <Text style={{ color: '#FFFFFF', fontSize: 20, fontFamily: 'Inter_700Bold' }}>
            Keşfet
          </Text>
        </View>
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
        style={{ flexGrow: 0 }}
        contentContainerStyle={{ paddingHorizontal: 12, paddingVertical: 4, gap: 8 }}
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
              <Ionicons name={cat.icon} size={26} color={isActive ? '#FFFFFF' : '#94A3B8'} />
            </TouchableOpacity>
          );
        })}
      </ScrollView>

      {/* Ürün Grid */}
      <View style={{ flex: 1, marginTop: 16 }}>
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
          <ScrollView
            showsVerticalScrollIndicator={false}
            contentContainerStyle={{ paddingHorizontal: 8, paddingBottom: 100 }}
          >
            {productGroups.map((group, gi) => (
              <View key={group.featured.id + gi}>

                {/* Üst blok: tek/çift gruba göre featured sol ↔ sağ */}
                <View style={{ flexDirection: 'row', height: FEATURED_ROW_HEIGHT, marginBottom: 0 }}>
                  {gi % 2 === 0 ? (
                    <>
                      <FeaturedCard product={group.featured} />
                      <View style={{ flex: 1, margin: 2, gap: 4 }}>
                        {group.sideCards.map((item) => <SideCard key={item.id} product={item} />)}
                      </View>
                    </>
                  ) : (
                    <>
                      <View style={{ flex: 1, margin: 2, gap: 4 }}>
                        {group.sideCards.map((item) => <SideCard key={item.id} product={item} />)}
                      </View>
                      <FeaturedCard product={group.featured} />
                    </>
                  )}
                </View>

                {/* Alt satır: 3 normal kart */}
                <View style={{ flexDirection: 'row' }}>
                  {group.belowCards.map((item) => (
                    <ProductGridCard key={item.id} product={item} />
                  ))}
                </View>

              </View>
            ))}
          </ScrollView>
        )}
      </View>
      </Animated.View>
    </SafeAreaView>
  );
}
