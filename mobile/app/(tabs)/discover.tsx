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
import { PrialLoader } from '@/components/ui/PrialLoader';
import client from '@/api/client';
import { ENDPOINTS } from '@/constants/api';
import type { ProductResponse } from '@/types/api';
import Animated from 'react-native-reanimated';
import { useFadeIn } from '@/hooks/useFadeIn';
import { imageSource } from '@/utils/imageSource';
import { useAuthStore } from '@/store/authStore';
import { openAlarmSheet } from '@/store/alarmSheetStore';
import { showAlert } from '@/store/alertStore';

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
const SIDE_IMAGE_H = 76;

const fmtPrice = (price: number | null) =>
  price != null ? Math.round(price).toLocaleString('tr-TR') + ' ₺' : '-';

const CATEGORIES: { label: string; slug: string | null; icon: React.ComponentProps<typeof Ionicons>['name'] }[] = [
  { label: 'Tümü',       slug: null,                    icon: 'apps' },
  { label: 'Telefon',    slug: 'akilli-telefon',         icon: 'phone-portrait' },
  { label: 'Laptop',     slug: 'laptop',                 icon: 'laptop' },
  { label: 'Tablet',     slug: 'tablet',                 icon: 'tablet-portrait' },
  { label: 'Televizyon', slug: 'televizyon',             icon: 'tv' },
  { label: 'Kulaklık',   slug: 'kulaklik-ses',           icon: 'headset' },
  { label: 'Saat',       slug: 'akilli-saat',            icon: 'watch' },
  { label: 'Fotoğraf',   slug: 'fotograf-makinesi',      icon: 'camera' },
  { label: 'Oyun',       slug: 'oyun-gaming',            icon: 'game-controller' },
  { label: 'PC',         slug: 'bilgisayar-bilesenleri', icon: 'desktop' },
  { label: 'Akıllı Ev',  slug: 'akilli-ev',              icon: 'home' },
  { label: 'Spor',       slug: 'spor-fitness',           icon: 'barbell' },
  { label: 'Mobilya',    slug: 'mobilya-ofis',           icon: 'bed' },
  { label: 'Sneaker',    slug: 'sneaker',                icon: 'footsteps' },
  { label: 'Outdoor',    slug: 'outdoor-mont',           icon: 'rainy' },
  { label: 'Çanta',      slug: 'canta-aksesuar',         icon: 'bag' },
  { label: 'Kol Saati',  slug: 'kol-saati',              icon: 'time' },
  { label: 'Giyim',      slug: 'premium-giyim',          icon: 'shirt' },
];

// ─── Büyük öne çıkan kart (soldaki 2/3) ──────────────────────────────────────

function FeaturedCard({ product }: { product: ProductResponse }) {
  const [imgError, setImgError] = useState(false);
  const isAuthenticated = useAuthStore((s) => s.isAuthenticated);
  const store = product.stores?.[0];
  const price = store?.current_price;
  const priceStr = fmtPrice(price);
  const drop = (() => {
    if (store?.discount_percent && store.discount_percent > 0) return store.discount_percent;
    const cur = Number(store?.current_price);
    const orig = Number(store?.original_price);
    if (orig > cur && cur > 0 && orig > 0) return Math.round((orig - cur) / orig * 100);
    return null;
  })();

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
      storeUrl: store?.url ?? null,
      currentPrice: price != null ? Number(price) : null,
    });
  };

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
      <View style={{ flex: 1, backgroundColor: CARD_BG, padding: 10 }}>
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
              <Ionicons name="cube-outline" size={48} color="#94A3B8" />
            </View>
          )}

          {/* Sol üst: düşüş varsa yeşil badge, yoksa "ÖNE ÇIKAN" */}
          {drop ? (
            <View style={{
              position: 'absolute', top: 8, left: 8,
              backgroundColor: '#22C55E', borderRadius: 5,
              paddingHorizontal: 7, paddingVertical: 3,
            }}>
              <Text style={{ color: '#fff', fontSize: 10, fontFamily: 'Inter_700Bold' }}>
                ↓%{drop}
              </Text>
            </View>
          ) : (
            <View style={{
              position: 'absolute', top: 8, left: 8,
              backgroundColor: '#1D4ED8', borderRadius: 5,
              paddingHorizontal: 7, paddingVertical: 3,
            }}>
              <Text style={{ color: '#fff', fontSize: 9, fontFamily: 'Inter_700Bold', letterSpacing: 0.8 }}>
                ÖNE ÇIKAN
              </Text>
            </View>
          )}

          {/* Sağ üst: talep oluştur butonu */}
          <TouchableOpacity
            onPress={handleAlarmPress}
            activeOpacity={0.85}
            style={{
              position: 'absolute', top: 8, right: 8,
              width: 26, height: 26, borderRadius: 13,
              backgroundColor: '#1D4ED8',
              justifyContent: 'center', alignItems: 'center',
            }}
          >
            <Ionicons name="add" size={18} color="#FFFFFF" />
          </TouchableOpacity>
        </View>
      </View>

      {/* Bilgi */}
      <View style={{ padding: 10, gap: 4 }}>
        <Text
          style={{ color: '#FFFFFF', fontSize: 12, fontFamily: 'Inter_600SemiBold', lineHeight: 16 }}
          numberOfLines={2}
        >
          {product.title}
        </Text>
        <View style={{ flexDirection: 'row', alignItems: 'center', justifyContent: 'space-between' }}>
          <Text style={{ color: '#FFFFFF', fontSize: 16, fontFamily: 'Inter_700Bold' }}>
            {priceStr}
          </Text>
          {product.alarm_count > 0 && (
            <View style={{ flexDirection: 'row', alignItems: 'center', gap: 3, backgroundColor: '#1D4ED820', borderRadius: 8, paddingHorizontal: 6, paddingVertical: 3 }}>
              <Ionicons name="pricetag-outline" size={12} color="#93C5FD" />
              <Text style={{ color: '#93C5FD', fontSize: 12, fontFamily: 'Inter_700Bold' }}>
                {product.alarm_count.toLocaleString('tr-TR')} Talep
              </Text>
            </View>
          )}
        </View>
      </View>
    </TouchableOpacity>
  );
}

// ─── Yan küçük kart (sağdaki 1/3, 2 adet dikey) ──────────────────────────────

function SideCard({ product }: { product: ProductResponse }) {
  const [imgError, setImgError] = useState(false);
  const isAuthenticated = useAuthStore((s) => s.isAuthenticated);
  const store = product.stores?.[0];
  const price = store?.current_price;
  const priceStr = fmtPrice(price);
  const drop = (() => {
    if (store?.discount_percent && store.discount_percent > 0) return store.discount_percent;
    const cur = Number(store?.current_price);
    const orig = Number(store?.original_price);
    if (orig > cur && cur > 0 && orig > 0) return Math.round((orig - cur) / orig * 100);
    return null;
  })();

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
      storeUrl: store?.url ?? null,
      currentPrice: price != null ? Number(price) : null,
    });
  };

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
      {/* Sabit yükseklik görsel alanı */}
      <View style={{ height: SIDE_IMAGE_H, backgroundColor: CARD_BG, padding: 6 }}>
        <View style={{ flex: 1, backgroundColor: '#FFFFFF', borderRadius: 8, overflow: 'hidden' }}>
          {product.image_url && !imgError ? (
            <Image
              source={imageSource(product.image_url)}
              style={{ width: '100%', height: '100%' }}
              contentFit="contain"
              onError={() => setImgError(true)}
            />
          ) : (
            <View style={{ flex: 1, justifyContent: 'center', alignItems: 'center' }}>
              <Ionicons name="cube-outline" size={22} color="#94A3B8" />
            </View>
          )}
          {/* Sol üst: düşüş badge */}
          {!!drop && (
            <View style={{
              position: 'absolute', top: 5, left: 5,
              backgroundColor: '#22C55E', borderRadius: 4,
              paddingHorizontal: 4, paddingVertical: 2,
            }}>
              <Text style={{ color: '#fff', fontSize: 8, fontFamily: 'Inter_700Bold' }}>
                ↓%{drop}
              </Text>
            </View>
          )}

          {/* Sağ üst: talep oluştur butonu */}
          <TouchableOpacity
            onPress={handleAlarmPress}
            activeOpacity={0.85}
            style={{
              position: 'absolute', top: 5, right: 5,
              width: 20, height: 20, borderRadius: 10,
              backgroundColor: '#1D4ED8',
              justifyContent: 'center', alignItems: 'center',
            }}
          >
            <Ionicons name="add" size={14} color="#FFFFFF" />
          </TouchableOpacity>
        </View>
      </View>

      {/* Yazı */}
      <View style={{ flex: 1, paddingHorizontal: 6, paddingVertical: 4, justifyContent: 'space-between' }}>
        <Text
          style={{ color: '#FFFFFF', fontSize: 10, fontFamily: 'Inter_500Medium', lineHeight: 13 }}
          numberOfLines={2}
        >
          {product.title}
        </Text>
        <View style={{ flexDirection: 'row', alignItems: 'center', justifyContent: 'space-between' }}>
          <Text style={{ color: '#FFFFFF', fontSize: 12, fontFamily: 'Inter_700Bold' }}>
            {priceStr}
          </Text>
          {product.alarm_count > 0 ? (
            <View style={{ flexDirection: 'row', alignItems: 'center', gap: 2, backgroundColor: '#1D4ED820', borderRadius: 7, paddingHorizontal: 5, paddingVertical: 2 }}>
              <Ionicons name="pricetag-outline" size={10} color="#93C5FD" />
              <Text style={{ color: '#93C5FD', fontSize: 10, fontFamily: 'Inter_700Bold' }}>
                {product.alarm_count.toLocaleString('tr-TR')} Talep
              </Text>
            </View>
          ) : null}
        </View>
      </View>
    </TouchableOpacity>
  );
}

// ─── Normal 3'lü grid kartı ────────────────────────────────────────────────────

function ProductGridCard({ product }: { product: ProductResponse }) {
  const [imgError, setImgError] = useState(false);
  const isAuthenticated = useAuthStore((s) => s.isAuthenticated);
  const store = product.stores?.[0];
  const price = store?.current_price;
  const discount = store?.discount_percent;
  const priceStr = fmtPrice(price);

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
      storeUrl: store?.url ?? null,
      currentPrice: price != null ? Number(price) : null,
    });
  };

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
      <View style={{ width: '100%', height: 100, backgroundColor: CARD_BG, padding: 8 }}>
        <View style={{ flex: 1, backgroundColor: '#FFFFFF', borderRadius: 8, overflow: 'hidden' }}>
          {product.image_url && !imgError ? (
            <Image
              source={imageSource(product.image_url)}
              style={{ width: '100%', height: '100%' }}
              contentFit="contain"
              onError={() => setImgError(true)}
            />
          ) : (
            <View style={{ flex: 1, justifyContent: 'center', alignItems: 'center' }}>
              <Ionicons name="cube-outline" size={36} color="#94A3B8" />
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
          {/* Talep oluştur — sağ üst yuvarlak buton */}
          <TouchableOpacity
            onPress={handleAlarmPress}
            activeOpacity={0.85}
            style={{
              position: 'absolute', top: 6, right: 6,
              width: 22, height: 22, borderRadius: 11,
              backgroundColor: '#1D4ED8',
              justifyContent: 'center', alignItems: 'center',
            }}
          >
            <Ionicons name="add" size={15} color="#FFFFFF" />
          </TouchableOpacity>
        </View>
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
          {product.alarm_count > 0 && (
            <View style={{ flexDirection: 'row', alignItems: 'center', gap: 2, backgroundColor: '#1D4ED820', borderRadius: 7, paddingHorizontal: 5, paddingVertical: 2 }}>
              <Ionicons name="pricetag-outline" size={10} color="#93C5FD" />
              <Text style={{ color: '#93C5FD', fontSize: 10, fontFamily: 'Inter_700Bold' }}>
                {product.alarm_count.toLocaleString('tr-TR')} Talep
              </Text>
            </View>
          )}
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
          params: { q: q.trim(), page_size: 50 },
        });
        setProducts(res.data);
      } else if (category) {
        const res = await client.get<ProductResponse[]>(
          ENDPOINTS.DISCOVER_CATEGORY_PRODUCTS(category),
          { params: { page_size: 50 } },
        );
        setProducts(res.data);
      } else {
        const res = await client.get<ProductResponse[]>('/discover/products', {
          params: { page_size: 50, sort_by: 'alarm_count' },
        });
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
            colors={['#0D2060', '#1D4ED8']}
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
                backgroundColor: isActive ? '#1D4ED8' : '#1E293B',
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
          <PrialLoader />
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
