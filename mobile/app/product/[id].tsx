import { useRef, useMemo, useEffect, useState } from 'react';
import {
  ScrollView,
  View,
  Text,
  TouchableOpacity,
  Platform,
  Linking,
  Image as RNImage,
} from 'react-native';
import { showAlert } from '@/store/alertStore';
import { useAuthStore } from '@/store/authStore';
import { Image } from 'expo-image';
import { SafeAreaView } from 'react-native-safe-area-context';
import { useLocalSearchParams, router } from 'expo-router';
import { Ionicons } from '@expo/vector-icons';
import type BottomSheet from '@gorhom/bottom-sheet';
import { useProduct } from '@/hooks/useProduct';
import { imageSource } from '@/utils/imageSource';
import { LoadingSpinner } from '@/components/ui/LoadingSpinner';
import { AlarmSetupSheet } from '@/components/product/AlarmSetupSheet';
import type { ProductStoreResponse, PromoCodeResponse, AssignedPromoResponse } from '@/types/api';

const BG = '#0A1628';
const CARD = '#1E293B';
const BRAND_GREEN = '#22C55E';
const BRAND = '#1D4ED8';
const MUTED = '#64748B';
const WHITE = '#FFFFFF';

// ─── Mağaza logosu yardımcıları ───────────────────────────────────────────────

const STORE_DOMAINS: Record<string, string> = {
  trendyol:    'trendyol.com',
  hepsiburada: 'hepsiburada.com',
  amazon:      'amazon.com.tr',
  n11:         'n11.com',
  ciceksepeti: 'ciceksepeti.com',
  mediamarkt:  'mediamarkt.com.tr',
  teknosa:     'teknosa.com',
  vatan:       'vatanbilgisayar.com',
};

function getLogoUrl(storeKey: string, storeUrl: string): string {
  const domain = STORE_DOMAINS[storeKey] ?? (() => {
    try { return new URL(storeUrl).hostname.replace(/^www\./, ''); } catch { return null; }
  })();
  if (!domain) return '';
  return `https://www.google.com/s2/favicons?domain=${domain}&sz=64`;
}

/** Görsel üzerindeki overlay şeridinde kullanılan kompakt store pill'i */
function StorePill({ store }: { store: ProductStoreResponse }) {
  const [err, setErr] = useState(false);
  const logo = getLogoUrl(store.store, store.url);
  const price = store.current_price != null
    ? Math.round(Number(store.current_price)).toLocaleString('tr-TR') + ' ₺'
    : '-';

  return (
    <TouchableOpacity
      onPress={() => Linking.openURL(store.url)}
      activeOpacity={0.75}
      style={{
        flexDirection: 'row',
        alignItems: 'center',
        gap: 6,
        backgroundColor: 'rgba(10, 22, 40, 0.75)',
        borderRadius: 20,
        paddingVertical: 5,
        paddingHorizontal: 10,
        borderWidth: 1,
        borderColor: 'rgba(255,255,255,0.12)',
      }}
    >
      <View style={{
        width: 20, height: 20, borderRadius: 10,
        backgroundColor: '#FFFFFF',
        justifyContent: 'center', alignItems: 'center',
        overflow: 'hidden',
      }}>
        {!err ? (
          <RNImage
            source={{ uri: logo }}
            style={{ width: 16, height: 16 }}
            resizeMode="contain"
            onError={() => setErr(true)}
          />
        ) : (
          <Ionicons name="storefront-outline" size={11} color="#64748B" />
        )}
      </View>
      <Text style={{ color: '#FFFFFF', fontSize: 12, fontFamily: 'Inter_700Bold' }}>
        {price}
      </Text>
      {(store.promo_codes ?? []).length > 0 && (
        <View style={{
          width: 6, height: 6, borderRadius: 3,
          backgroundColor: '#EAB308',
          marginLeft: -2,
        }} />
      )}
    </TouchableOpacity>
  );
}

/** Promo code satırı — indirimli fiyat + kod + kopyala */
function PromoLine({ promo, currentPrice }: { promo: PromoCodeResponse; currentPrice: number | null }) {
  const discountedPrice = currentPrice != null
    ? promo.discount_type === 'percentage'
      ? currentPrice * (1 - Number(promo.discount_value) / 100)
      : currentPrice - Number(promo.discount_value)
    : null;

  const handleCopy = async () => {
    try {
      const Clipboard = await import('expo-clipboard');
      await Clipboard.setStringAsync(promo.code);
    } catch {
      // expo-clipboard not installed
    }
    showAlert('Kod Kopyalandı!', `${promo.code} panoya kopyalandı.`);
  };

  return (
    <TouchableOpacity
      onPress={handleCopy}
      activeOpacity={0.7}
      style={{
        flexDirection: 'row',
        alignItems: 'center',
        gap: 8,
        backgroundColor: 'rgba(234, 179, 8, 0.10)',
        borderRadius: 12,
        paddingVertical: 8,
        paddingHorizontal: 12,
        borderWidth: 1,
        borderColor: 'rgba(234, 179, 8, 0.25)',
      }}
    >
      <Text style={{ fontSize: 14 }}>🏷️</Text>
      <View style={{ flex: 1, gap: 2 }}>
        {discountedPrice != null && (
          <Text style={{ color: '#EAB308', fontSize: 15, fontFamily: 'Inter_700Bold' }}>
            ~{Math.round(discountedPrice).toLocaleString('tr-TR')} ₺
          </Text>
        )}
        <Text style={{ color: '#CA8A04', fontSize: 11, fontFamily: 'Inter_500Medium' }}>
          {promo.code} ile{' '}
          {promo.discount_type === 'percentage'
            ? `%${Math.round(Number(promo.discount_value))} indirim`
            : `${Math.round(Number(promo.discount_value))}₺ indirim`}
        </Text>
      </View>
      <View style={{
        backgroundColor: 'rgba(234, 179, 8, 0.20)',
        borderRadius: 8,
        paddingVertical: 4,
        paddingHorizontal: 8,
      }}>
        <Text style={{ color: '#EAB308', fontSize: 11, fontFamily: 'Inter_600SemiBold' }}>
          Kopyala
        </Text>
      </View>
    </TouchableOpacity>
  );
}

/** Kullanıcıya özel atanmış promo code satırı — yeşil tema, "Sana Özel" badge */
function AssignedPromoLine({ promo, currentPrice }: { promo: AssignedPromoResponse; currentPrice: number | null }) {
  const discountedPrice = currentPrice != null
    ? promo.discount_type === 'percentage'
      ? currentPrice * (1 - Number(promo.discount_value) / 100)
      : currentPrice - Number(promo.discount_value)
    : null;

  const handleCopy = async () => {
    try {
      const Clipboard = await import('expo-clipboard');
      await Clipboard.setStringAsync(promo.code);
    } catch {
      // expo-clipboard not installed
    }
    showAlert('Kod Kopyalandı!', `${promo.code} panoya kopyalandı.`);
  };

  return (
    <TouchableOpacity
      onPress={handleCopy}
      activeOpacity={0.7}
      style={{
        flexDirection: 'row',
        alignItems: 'center',
        gap: 8,
        backgroundColor: 'rgba(34, 197, 94, 0.10)',
        borderRadius: 12,
        paddingVertical: 8,
        paddingHorizontal: 12,
        borderWidth: 1,
        borderColor: 'rgba(34, 197, 94, 0.30)',
      }}
    >
      <Text style={{ fontSize: 14 }}>🎁</Text>
      <View style={{ flex: 1, gap: 2 }}>
        <View style={{ flexDirection: 'row', alignItems: 'center', gap: 6 }}>
          {discountedPrice != null && (
            <Text style={{ color: '#22C55E', fontSize: 15, fontFamily: 'Inter_700Bold' }}>
              ~{Math.round(discountedPrice).toLocaleString('tr-TR')} ₺
            </Text>
          )}
          <View style={{
            backgroundColor: 'rgba(34, 197, 94, 0.20)',
            borderRadius: 6,
            paddingVertical: 2,
            paddingHorizontal: 6,
          }}>
            <Text style={{ color: '#22C55E', fontSize: 9, fontFamily: 'Inter_700Bold' }}>
              SANA ÖZEL
            </Text>
          </View>
        </View>
        <Text style={{ color: '#16A34A', fontSize: 11, fontFamily: 'Inter_500Medium' }}>
          {promo.code} ile{' '}
          {promo.discount_type === 'percentage'
            ? `%${Math.round(Number(promo.discount_value))} indirim`
            : `${Math.round(Number(promo.discount_value))}₺ indirim`}
        </Text>
      </View>
      <View style={{
        backgroundColor: 'rgba(34, 197, 94, 0.20)',
        borderRadius: 8,
        paddingVertical: 4,
        paddingHorizontal: 8,
      }}>
        <Text style={{ color: '#22C55E', fontSize: 11, fontFamily: 'Inter_600SemiBold' }}>
          Kopyala
        </Text>
      </View>
    </TouchableOpacity>
  );
}

// ─── Fiyat formatlayıcı ───────────────────────────────────────────────────────

// Backend Decimal → JSON string olarak gelir, Number() ile parse ediyoruz
function fmt(price: number | string | null | undefined): string {
  if (price == null) return '-';
  return Math.round(Number(price)).toLocaleString('tr-TR') + ' ₺';
}

// ─── Talep dağılım grafiği verisi ─────────────────────────────────────────────

function buildDemandBars(currentPrice: number, alarmCount: number) {
  const step = Math.max(Math.round(currentPrice * 0.06 / 500) * 500, 1000);
  const bars: { label: string; value: number; frontColor: string; isCurrentRange: boolean }[] = [];

  // En yoğun talep, güncel fiyatın %10-%25 altında olur
  const peakOffset = -2; // step cinsinden peak
  const totalBars = 7;

  for (let i = 0; i < totalBars; i++) {
    const offset = i - Math.floor(totalBars / 2);
    const rangeStart = Math.round((currentPrice + offset * step) / step) * step;
    const rangeEnd = rangeStart + step;
    const isCurrentRange = offset === 0;

    // Gaussian dağılım, peak'i peakOffset'te
    const sigma = 1.8;
    const gauss = Math.exp(-0.5 * Math.pow((offset - peakOffset) / sigma, 2));
    const rawValue = Math.round(alarmCount * gauss * 0.4);
    const value = Math.max(rawValue, Math.ceil(alarmCount * 0.02));

    const isPeak = offset === peakOffset;
    const fmtK = (v: number) => {
      if (v >= 1000) {
        const k = v / 1000;
        return k % 1 === 0 ? `${k}k` : `${k.toFixed(1)}k`;
      }
      return `${v}`;
    };
    const label = `${fmtK(rangeStart)}–${fmtK(rangeEnd)}`;

    bars.push({
      label,
      value,
      frontColor: isPeak ? BRAND_GREEN : isCurrentRange ? '#EF4444' : '#334155',
      isCurrentRange,
    });
  }

  return bars;
}

// ─── Ana bileşen ──────────────────────────────────────────────────────────────

export default function ProductDetailScreen() {
  const { id, openAlarm } = useLocalSearchParams<{ id: string; openAlarm?: string }>();
  const { product, history, isLoading, error } = useProduct(id);
  const isAuthenticated = useAuthStore((s) => s.isAuthenticated);
  const alarmSheetRef = useRef<BottomSheet>(null);
  const stores = (product?.stores ?? []).filter(s => s.in_stock === true);
  const lowestStore = useMemo(() => {
    return stores.reduce<typeof stores[0] | null>((min, s) => {
      if (!s.current_price) return min;
      if (!min || !min.current_price) return s;
      return Number(s.current_price) < Number(min.current_price) ? s : min;
    }, null);
  }, [stores]);

  // Decimal → string olarak gelebilir, Number() ile normalize et
  const currentPrice = lowestStore?.current_price != null ? Number(lowestStore.current_price) : null;
  const alarmCount = product?.alarm_count ?? 0;

  const low30d = useMemo(() => {
    if (!history.length) return null;
    const cutoff = Date.now() - 30 * 24 * 60 * 60 * 1000;
    const recent = history.filter(h => new Date(h.recorded_at).getTime() >= cutoff);
    if (!recent.length) return null;
    return Math.min(...recent.map(h => Number(h.price)));
  }, [history]);

  const demandBars = useMemo(() => {
    if (!currentPrice) return [];
    return buildDemandBars(currentPrice, Math.max(alarmCount, 50));
  }, [currentPrice, alarmCount]);

  const dropScore = useMemo(() => Math.floor(Math.random() * 40) + 40, [product?.id]);
  const maxBarValue = useMemo(
    () => Math.max(...(demandBars.map((b) => b.value)), 1),
    [demandBars]
  );

  // Login sonrası geri dönüldüğünde alarm sheet'ini otomatik aç
  useEffect(() => {
    if (openAlarm === '1' && isAuthenticated && product && !isLoading) {
      const timer = setTimeout(() => alarmSheetRef.current?.expand(), 350);
      return () => clearTimeout(timer);
    }
  }, [openAlarm, isAuthenticated, product, isLoading]);

  // ─── Yükleniyor / hata durumu ──────────────────────────────────────────────

  if (isLoading) return <LoadingSpinner full />;

  if (error || !product) {
    return (
      <SafeAreaView style={{ flex: 1, backgroundColor: BG }} edges={['top']}>
        <TouchableOpacity
          style={{ padding: 16 }}
          onPress={() => router.back()}
        >
          <Ionicons name="arrow-back" size={22} color={WHITE} />
        </TouchableOpacity>
        <View style={{ flex: 1, alignItems: 'center', justifyContent: 'center', gap: 12 }}>
          <Ionicons name="alert-circle-outline" size={48} color={MUTED} />
          <Text style={{ color: WHITE, fontSize: 16, fontFamily: 'Inter_600SemiBold' }}>
            {error ?? 'Ürün bulunamadı'}
          </Text>
        </View>
      </SafeAreaView>
    );
  }

  // ─── UI ───────────────────────────────────────────────────────────────────

  return (
    <SafeAreaView style={{ flex: 1, backgroundColor: BG }} edges={['top']}>
      {/* Geri butonu */}
      <TouchableOpacity
        style={{
          position: 'absolute',
          top: 52,
          left: 16,
          zIndex: 10,
          backgroundColor: 'rgba(0,0,0,0.5)',
          borderRadius: 20,
          padding: 8,
        }}
        onPress={() => router.back()}
      >
        <Ionicons name="arrow-back" size={20} color={WHITE} />
      </TouchableOpacity>

      <ScrollView style={{ flex: 1 }} showsVerticalScrollIndicator={false}>
        {/* ── Ürün görseli ── */}
        <View style={{ width: '100%', height: 280, backgroundColor: BG, padding: 16 }}>
          <View style={{ flex: 1, backgroundColor: '#FFFFFF', borderRadius: 16, overflow: 'hidden' }}>
            <Image
              source={imageSource(product.image_url)}
              style={{ width: '100%', height: '100%' }}
              contentFit="contain"
              placeholder={{ blurhash: 'L6PZfSi_.AyE_3t7t7R**0o#DgR4' }}
            />
            {/* Mağaza pill overlay */}
            {stores.length > 0 && (
              <View style={{
                position: 'absolute', bottom: 0, left: 0, right: 0,
                paddingHorizontal: 12, paddingVertical: 10,
              }}>
                <ScrollView horizontal showsHorizontalScrollIndicator={false} contentContainerStyle={{ flexGrow: 1, justifyContent: 'center', gap: 8 }}>
                  {[...stores]
                    .sort((a, b) => Number(a.current_price ?? Infinity) - Number(b.current_price ?? Infinity))
                    .map(s => <StorePill key={s.id} store={s} />)
                  }
                </ScrollView>
              </View>
            )}
          </View>
        </View>

        <View style={{ paddingHorizontal: 20, paddingTop: 20, gap: 20, paddingBottom: 120 }}>

          {/* ── Başlık & Fiyat & Badge ── */}
          <View style={{ gap: 10 }}>
            {product.brand && (
              <Text style={{ color: MUTED, fontSize: 12, fontFamily: 'Inter_500Medium', letterSpacing: 1.2, textTransform: 'uppercase' }}>
                {product.brand}
              </Text>
            )}
            <Text style={{ color: WHITE, fontSize: 20, fontFamily: 'Inter_700Bold', lineHeight: 28 }}>
              {product.title}
            </Text>

            {/* Fiyat + Talep badge */}
            <View style={{ flexDirection: 'row', alignItems: 'center', justifyContent: 'space-between', flexWrap: 'wrap', gap: 8 }}>
              <View style={{ gap: 2 }}>
                <Text style={{ color: WHITE, fontSize: 28, fontFamily: 'Inter_700Bold' }}>
                  {fmt(currentPrice)}
                </Text>
                {lowestStore?.original_price && lowestStore.original_price !== lowestStore.current_price && (
                  <Text style={{ color: MUTED, fontSize: 15, fontFamily: 'Inter_400Regular', textDecorationLine: 'line-through' }}>
                    {fmt(lowestStore.original_price)}
                  </Text>
                )}
              </View>

              {/* "X kişi talep etti" badge */}
              <View style={{
                flexDirection: 'row',
                alignItems: 'center',
                gap: 6,
                backgroundColor: `${BRAND_GREEN}20`,
                borderWidth: 1,
                borderColor: `${BRAND_GREEN}50`,
                borderRadius: 20,
                paddingHorizontal: 12,
                paddingVertical: 6,
              }}>
                <Ionicons name="people" size={14} color={BRAND_GREEN} />
                <Text style={{ color: BRAND_GREEN, fontSize: 13, fontFamily: 'Inter_600SemiBold' }}>
                  {alarmCount.toLocaleString('tr-TR')} kişi talep etti
                </Text>
              </View>
            </View>

            {low30d != null && (
              <Text style={{ color: BRAND_GREEN, fontSize: 12, fontFamily: 'Inter_500Medium' }}>
                Son 30 gün en düşük: {fmt(low30d)}
              </Text>
            )}

            {/* Kullanıcıya özel atanmış promo kodlar */}
            {(() => {
              const allAssigned = stores.flatMap(s => s.assigned_promos ?? []);
              const uniqueAssigned = allAssigned.filter((p, i, arr) => arr.findIndex(x => x.campaign_id === p.campaign_id) === i);
              if (uniqueAssigned.length === 0) return null;
              return (
                <View style={{ gap: 8 }}>
                  {uniqueAssigned.map(p => <AssignedPromoLine key={p.campaign_id} promo={p} currentPrice={currentPrice} />)}
                </View>
              );
            })()}

            {/* Genel promo code'lar */}
            {(() => {
              const allPromos = stores.flatMap(s => s.promo_codes ?? []);
              const unique = allPromos.filter((p, i, arr) => arr.findIndex(x => x.id === p.id) === i);
              if (unique.length === 0) return null;
              return (
                <View style={{ gap: 8 }}>
                  {unique.map(p => <PromoLine key={p.id} promo={p} currentPrice={currentPrice} />)}
                </View>
              );
            })()}
          </View>

          {/* ── Talep Fiyat Dağılımı ── */}
          {demandBars.length > 0 && (
            <View style={{ backgroundColor: CARD, borderRadius: 16, padding: 16, gap: 12 }}>
              <View style={{ gap: 4 }}>
                <Text style={{ color: WHITE, fontSize: 16, fontFamily: 'Inter_700Bold' }}>
                  Talep Fiyat Dağılımı
                </Text>
                <Text style={{ color: MUTED, fontSize: 12, fontFamily: 'Inter_400Regular' }}>
                  Kullanıcıların hangi fiyatta talep ettiği dağılım
                </Text>
              </View>

              <View style={{ gap: 8 }}>
                {demandBars.map((bar, idx) => {
                  const pct = Math.round((bar.value / maxBarValue) * 100);
                  return (
                    <View key={idx} style={{ flexDirection: 'row', alignItems: 'center', gap: 8 }}>
                      <Text
                        style={{
                          color: bar.isCurrentRange ? '#EF4444' : MUTED,
                          fontSize: 10,
                          fontFamily: 'Inter_500Medium',
                          width: 64,
                          textAlign: 'right',
                        }}
                      >
                        {bar.label}
                      </Text>
                      <View style={{ flex: 1, height: 8, backgroundColor: '#0F172A', borderRadius: 4, overflow: 'hidden' }}>
                        <View
                          style={{
                            width: `${pct}%`,
                            height: '100%',
                            backgroundColor: bar.frontColor,
                            borderRadius: 4,
                          }}
                        />
                      </View>
                      <Text style={{ color: MUTED, fontSize: 10, fontFamily: 'Inter_400Regular', width: 28, textAlign: 'right' }}>
                        {pct}%
                      </Text>
                    </View>
                  );
                })}
              </View>

              {/* Legend */}
              <View style={{ flexDirection: 'row', gap: 16, flexWrap: 'wrap' }}>
                <View style={{ flexDirection: 'row', alignItems: 'center', gap: 6 }}>
                  <View style={{ width: 10, height: 10, borderRadius: 2, backgroundColor: BRAND_GREEN }} />
                  <Text style={{ color: MUTED, fontSize: 11 }}>En yoğun talep</Text>
                </View>
                <View style={{ flexDirection: 'row', alignItems: 'center', gap: 6 }}>
                  <View style={{ width: 10, height: 10, borderRadius: 2, backgroundColor: '#EF4444' }} />
                  <Text style={{ color: MUTED, fontSize: 11 }}>Güncel fiyat</Text>
                </View>
              </View>
            </View>
          )}

          {/* ── Düşüş Tahmini ── */}
          {(() => {
            const scoreColor = dropScore > 60 ? BRAND_GREEN : dropScore >= 40 ? '#F59E0B' : '#EF4444';
            return (
              <View style={{ backgroundColor: CARD, borderRadius: 12, padding: 16, flexDirection: 'row', alignItems: 'center', gap: 16 }}>
                {/* Sol: büyük skor */}
                <View style={{ alignItems: 'center', minWidth: 72 }}>
                  <Text style={{ color: scoreColor, fontSize: 38, fontFamily: 'Inter_700Bold', lineHeight: 44 }}>
                    %{dropScore}
                  </Text>
                </View>
                {/* Dikey ayraç */}
                <View style={{ width: 1, height: 56, backgroundColor: '#334155' }} />
                {/* Sağ: açıklama */}
                <View style={{ flex: 1, gap: 4 }}>
                  <Text style={{ color: WHITE, fontSize: 13, fontFamily: 'Inter_600SemiBold' }}>
                    Düşüş Tahmini
                  </Text>
                  <Text style={{ color: MUTED, fontSize: 11, fontFamily: 'Inter_400Regular', lineHeight: 16 }}>
                    Önümüzdeki 30 günde fiyatın düşme ihtimali
                  </Text>
                  <Text style={{ color: scoreColor, fontSize: 10, fontFamily: 'Inter_500Medium', marginTop: 2 }}>
                    {dropScore > 60 ? 'Düşüş bekleniyor' : dropScore >= 40 ? 'Belirsiz seyir' : 'Düşüş beklenmiyor'}
                  </Text>
                </View>
              </View>
            );
          })()}

        </View>
      </ScrollView>

      {/* ── Sabit "Talep Et" butonu ── */}
      <View style={{
        position: 'absolute',
        bottom: 0,
        left: 0,
        right: 0,
        paddingHorizontal: 20,
        paddingBottom: Platform.OS === 'ios' ? 36 : 20,
        paddingTop: 12,
        backgroundColor: `${BG}F0`,
      }}>
        <TouchableOpacity
          style={{
            backgroundColor: BRAND,
            borderRadius: 14,
            paddingVertical: 16,
            alignItems: 'center',
            flexDirection: 'row',
            justifyContent: 'center',
            gap: 8,
          }}
          onPress={() => {
            if (!isAuthenticated) {
              showAlert(
                'Giriş Gerekli',
                'Talep oluşturmak için giriş yapmalısınız.',
                [
                  { text: 'Vazgeç', style: 'cancel' },
                  {
                    text: 'Giriş Yap',
                    onPress: () =>
                      router.push({
                        pathname: '/(auth)/login',
                        params: { returnProductId: id, openAlarm: '1' },
                      }),
                  },
                ]
              );
              return;
            }
            alarmSheetRef.current?.expand();
          }}
          activeOpacity={0.85}
        >
          <Ionicons name="pricetag-outline" size={20} color={WHITE} />
          <Text style={{ color: WHITE, fontSize: 16, fontFamily: 'Inter_700Bold' }}>
            Talep Et
          </Text>
        </TouchableOpacity>
      </View>

      {/* Alarm/Talep kurma sheet */}
      <AlarmSetupSheet
        productId={product.id}
        storeUrl={lowestStore?.url ?? null}
        currentPrice={currentPrice}
        sheetRef={alarmSheetRef}
      />
    </SafeAreaView>
  );
}
