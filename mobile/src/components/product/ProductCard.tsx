import { useState, useMemo } from 'react';
import { TouchableOpacity, Text, View, Image as RNImage } from 'react-native';
import { Image } from 'expo-image';
import { router } from 'expo-router';
import { Ionicons } from '@expo/vector-icons';
import { DiscountBadge } from '@/components/ui/DiscountBadge';
import { SignalBadge } from '@/components/ui/SignalBadge';
import { useAuthStore } from '@/store/authStore';
import { openAlarmSheet } from '@/store/alarmSheetStore';
import { showAlert } from '@/store/alertStore';
import type { ProductResponse, ProductStoreResponse, StoreName } from '@/types/api';
import { imageSource } from '@/utils/imageSource';

function extractCardSummary(text: string): string {
  let clean = text;
  if (clean.trimStart().startsWith('{')) {
    try {
      const parsed = JSON.parse(clean);
      clean = parsed.summary || clean;
    } catch {
      const match = clean.match(/"summary"\s*:\s*"([^"]+)"/);
      if (match) clean = match[1];
    }
  }
  return clean.split('.').slice(0, 2).join('.').trim() + '.';
}

interface ProductCardProps {
  product: ProductResponse;
  store?: ProductStoreResponse;
}

const STORE_LABELS: Record<string, string> = {
  trendyol: 'Trendyol',
  hepsiburada: 'Hepsiburada',
  amazon: 'Amazon',
  n11: 'N11',
  ciceksepeti: 'Çiçeksepeti',
  mediamarkt: 'MediaMarkt',
  teknosa: 'Teknosa',
  vatan: 'Vatan',
  other: 'Diğer',
};

const STORE_COLORS: Record<string, string> = {
  trendyol: '#F27A1A',
  hepsiburada: '#FF6000',
  amazon: '#FF9900',
  n11: '#6B21A8',
  ciceksepeti: '#E11D48',
  mediamarkt: '#CC0000',
  teknosa: '#1D4ED8',
  vatan: '#DC2626',
  other: '#334155',
};

const STORE_DOMAINS: Record<string, string> = {
  trendyol: 'trendyol.com',
  hepsiburada: 'hepsiburada.com',
  amazon: 'amazon.com.tr',
  n11: 'n11.com',
  ciceksepeti: 'ciceksepeti.com',
  mediamarkt: 'mediamarkt.com.tr',
  teknosa: 'teknosa.com',
  vatan: 'vatanbilgisayar.com',
};

/** Mağaza başına en düşük fiyatlı store'u döner */
function getBestPerStore(stores: ProductStoreResponse[]): ProductStoreResponse[] {
  const map = new Map<string, ProductStoreResponse>();
  for (const s of stores) {
    if (!s.in_stock || s.current_price == null) continue;
    const existing = map.get(s.store);
    if (!existing || Number(s.current_price) < Number(existing.current_price!)) {
      map.set(s.store, s);
    }
  }
  // Fiyata göre sırala (en ucuz önce)
  return Array.from(map.values()).sort(
    (a, b) => Number(a.current_price!) - Number(b.current_price!)
  );
}

export function ProductCard({ product, store, width = 160 }: ProductCardProps & { width?: number }) {
  const [imgError, setImgError] = useState(false);
  const isAuthenticated = useAuthStore((s) => s.isAuthenticated);

  const bestPerStore = useMemo(() => getBestPerStore(product.stores), [product.stores]);

  const activeStore = store ?? bestPerStore[0] ?? product.stores[0];

  const price = activeStore?.current_price;
  const discount = activeStore?.discount_percent;

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

  const imgSrc = imageSource(product.image_url);
  const hasImage = !!imgSrc && !imgError;

  return (
    <TouchableOpacity
      onPress={() => router.push(`/product/${product.id}`)}
      activeOpacity={0.85}
      style={{
        width,
        backgroundColor: '#1E293B',
        borderRadius: 8,
        overflow: 'hidden',
      }}
    >
      {/* Görsel alanı */}
      <View style={{ width: '100%', aspectRatio: 1, backgroundColor: '#1E293B', padding: 8 }}>
        <View style={{ flex: 1, backgroundColor: '#FFFFFF', borderRadius: 10, overflow: 'hidden' }}>
          {hasImage ? (
            <Image
              source={imgSrc}
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

          {/* SignalBadge — sol alt */}
          {product.recommendation && (
            <View style={{ position: 'absolute', bottom: 6, left: 6 }}>
              <SignalBadge recommendation={product.recommendation} size="sm" showLabel={false} />
            </View>
          )}

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
      <View style={{ paddingHorizontal: 8, paddingTop: 4, paddingBottom: 8, gap: 4 }}>
        <Text
          style={{ color: '#FFFFFF', fontSize: 11, fontFamily: 'Inter_600SemiBold', lineHeight: 15 }}
          numberOfLines={2}
        >
          {product.short_title || product.title}
        </Text>

        {/* Fiyat */}
        <Text style={{ color: '#FFFFFF', fontSize: 14, fontFamily: 'Inter_700Bold' }}>
          {price != null ? Math.round(Number(price)).toLocaleString('tr-TR') + ' ₺' : '-'}
        </Text>

        {/* Talep sayısı */}
        {product.alarm_count > 0 && (
          <View style={{ flexDirection: 'row', alignItems: 'center', gap: 3 }}>
            <Ionicons name="pricetag-outline" size={10} color="#93C5FD" />
            <Text style={{ color: '#93C5FD', fontSize: 10, fontFamily: 'Inter_600SemiBold' }}>
              {product.alarm_count.toLocaleString('tr-TR')} talep
            </Text>
          </View>
        )}
      </View>
    </TouchableOpacity>
  );
}

/** Mağaza logosu + en düşük fiyat chip'i */
function StorePriceChip({ store }: { store: ProductStoreResponse }) {
  const [logoError, setLogoError] = useState(false);
  const color = STORE_COLORS[store.store] ?? '#334155';
  const domain = STORE_DOMAINS[store.store] ?? 'example.com';
  const priceStr = store.current_price != null
    ? Math.round(Number(store.current_price)).toLocaleString('tr-TR') + '₺'
    : '-';

  return (
    <View
      style={{
        flexDirection: 'row',
        alignItems: 'center',
        gap: 3,
        backgroundColor: color + '20',
        borderRadius: 6,
        paddingHorizontal: 5,
        paddingVertical: 3,
      }}
    >
      {!logoError ? (
        <RNImage
          source={{ uri: `https://logo.clearbit.com/${domain}` }}
          style={{ width: 12, height: 12, borderRadius: 2 }}
          resizeMode="contain"
          onError={() => setLogoError(true)}
        />
      ) : (
        <View style={{ width: 12, height: 12, borderRadius: 2, backgroundColor: color }}>
          <Ionicons name="storefront" size={8} color="#FFFFFF" style={{ margin: 2 }} />
        </View>
      )}
      <Text style={{ color: '#FFFFFF', fontSize: 10, fontFamily: 'Inter_700Bold' }}>
        {priceStr}
      </Text>
    </View>
  );
}
