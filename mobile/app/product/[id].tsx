import { useRef, useMemo } from 'react';
import {
  ScrollView,
  View,
  Text,
  TouchableOpacity,
  Alert,
  useWindowDimensions,
  Platform,
} from 'react-native';
import { Image } from 'expo-image';
import { SafeAreaView } from 'react-native-safe-area-context';
import { useLocalSearchParams, router } from 'expo-router';
import { Ionicons } from '@expo/vector-icons';
import type BottomSheet from '@gorhom/bottom-sheet';
import { BarChart, LineChart } from 'react-native-gifted-charts';
import { useProduct } from '@/hooks/useProduct';
import { LoadingSpinner } from '@/components/ui/LoadingSpinner';
import { AlarmSetupSheet } from '@/components/product/AlarmSetupSheet';

const BG = '#0A1628';
const CARD = '#1E293B';
const BRAND_GREEN = '#22C55E';
const BRAND_BLUE = '#1D4ED8';
const MUTED = '#64748B';
const WHITE = '#FFFFFF';

// ─── Fiyat formatlayıcı ───────────────────────────────────────────────────────

function fmt(price: number | null | undefined): string {
  if (price == null) return '-';
  return price.toLocaleString('tr-TR', { maximumFractionDigits: 0 }) + ' ₺';
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
    const label =
      rangeStart >= 1000
        ? `${Math.round(rangeStart / 1000)}k`
        : `${rangeStart}`;

    bars.push({
      label,
      value,
      frontColor: isPeak ? BRAND_GREEN : isCurrentRange ? '#EF4444' : '#334155',
      isCurrentRange,
    });
  }

  return bars;
}

// ─── Fiyat geçmişi verisi ─────────────────────────────────────────────────────

function buildLineData(history: { price: number; recorded_at: string }[]) {
  if (!history || history.length === 0) return [];
  const sorted = [...history].sort(
    (a, b) => new Date(a.recorded_at).getTime() - new Date(b.recorded_at).getTime()
  );
  // Son 30 nokta
  return sorted.slice(-30).map((h) => ({ value: h.price }));
}

// ─── Ana bileşen ──────────────────────────────────────────────────────────────

export default function ProductDetailScreen() {
  const { id } = useLocalSearchParams<{ id: string }>();
  const { product, history, isLoading, error } = useProduct(id);
  const alarmSheetRef = useRef<BottomSheet>(null);
  const { width } = useWindowDimensions();
  const chartWidth = width - 48; // padding

  const stores = product?.stores ?? [];
  const lowestStore = useMemo(() => {
    return stores.reduce<typeof stores[0] | null>((min, s) => {
      if (!s.current_price) return min;
      if (!min || !min.current_price) return s;
      return s.current_price < min.current_price ? s : min;
    }, null);
  }, [stores]);

  const currentPrice = lowestStore?.current_price ?? null;
  const alarmCount = product?.alarm_count ?? 0;

  const demandBars = useMemo(() => {
    if (!currentPrice) return [];
    return buildDemandBars(currentPrice, Math.max(alarmCount, 50));
  }, [currentPrice, alarmCount]);

  const lineData = useMemo(() => buildLineData(history ?? []), [history]);

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
        <Image
          source={{ uri: product.image_url ?? undefined }}
          style={{ width: '100%', height: 250, backgroundColor: CARD }}
          contentFit="cover"
          placeholder={{ blurhash: 'L6PZfSi_.AyE_3t7t7R**0o#DgR4' }}
        />

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

            {product.lowest_price_ever && (
              <Text style={{ color: BRAND_GREEN, fontSize: 12, fontFamily: 'Inter_500Medium' }}>
                En düşük fiyat: {fmt(product.lowest_price_ever)}
              </Text>
            )}
          </View>

          {/* ── Talep Fiyat Dağılımı ── */}
          {demandBars.length > 0 && (
            <View style={{ backgroundColor: CARD, borderRadius: 16, padding: 16, gap: 12 }}>
              <View style={{ gap: 4 }}>
                <Text style={{ color: WHITE, fontSize: 16, fontFamily: 'Inter_700Bold' }}>
                  Talep Fiyat Dağılımı
                </Text>
                <Text style={{ color: MUTED, fontSize: 12, fontFamily: 'Inter_400Regular' }}>
                  Kullanıcıların kaçta talep ettiği fiyat aralıkları
                </Text>
              </View>

              <View style={{ position: 'relative' }}>
                <BarChart
                  data={demandBars}
                  width={chartWidth - 32}
                  height={140}
                  barWidth={Math.floor((chartWidth - 80) / demandBars.length)}
                  spacing={6}
                  noOfSections={4}
                  yAxisTextStyle={{ color: MUTED, fontSize: 9 }}
                  xAxisLabelTextStyle={{ color: MUTED, fontSize: 9 }}
                  xAxisColor={MUTED}
                  yAxisColor={'transparent'}
                  hideRules
                  isAnimated
                  animationDuration={600}
                  backgroundColor={CARD}
                  roundedTop
                />

                {/* Kırmızı dikey çizgi — güncel fiyat */}
                {(() => {
                  const currentIdx = demandBars.findIndex((b) => b.isCurrentRange);
                  if (currentIdx < 0) return null;
                  const barWidth = Math.floor((chartWidth - 80) / demandBars.length);
                  const spacing = 6;
                  const leftOffset = 44 + currentIdx * (barWidth + spacing) + barWidth / 2;
                  return (
                    <View
                      pointerEvents="none"
                      style={{
                        position: 'absolute',
                        left: leftOffset,
                        top: 0,
                        bottom: 22,
                        width: 2,
                        backgroundColor: '#EF4444',
                        borderRadius: 1,
                        opacity: 0.9,
                      }}
                    />
                  );
                })()}
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

          {/* ── Fiyat Geçmişi ── */}
          <View style={{ backgroundColor: CARD, borderRadius: 16, padding: 16, gap: 12 }}>
            <View style={{ gap: 4 }}>
              <Text style={{ color: WHITE, fontSize: 16, fontFamily: 'Inter_700Bold' }}>
                Fiyat Geçmişi
              </Text>
              <Text style={{ color: MUTED, fontSize: 12, fontFamily: 'Inter_400Regular' }}>
                Son 30 kayıt
              </Text>
            </View>

            {lineData.length > 1 ? (
              <LineChart
                data={lineData}
                width={chartWidth - 32}
                height={140}
                color={BRAND_BLUE}
                thickness={2}
                noOfSections={4}
                yAxisTextStyle={{ color: MUTED, fontSize: 9 }}
                xAxisColor={MUTED}
                yAxisColor={'transparent'}
                hideDataPoints={lineData.length > 10}
                dataPointsColor={BRAND_BLUE}
                dataPointsRadius={3}
                curved
                areaChart
                startFillColor={`${BRAND_BLUE}40`}
                endFillColor={`${BRAND_BLUE}05`}
                startOpacity={0.6}
                endOpacity={0.05}
                hideRules
                isAnimated
                backgroundColor={CARD}
              />
            ) : (
              <View style={{ height: 100, alignItems: 'center', justifyContent: 'center', gap: 8 }}>
                <Ionicons name="analytics-outline" size={32} color={MUTED} />
                <Text style={{ color: MUTED, fontSize: 13 }}>Henüz yeterli fiyat geçmişi yok</Text>
              </View>
            )}
          </View>

          {/* ── Mağazalar ── */}
          {stores.length > 0 && (
            <View style={{ backgroundColor: CARD, borderRadius: 16, padding: 16, gap: 12 }}>
              <Text style={{ color: WHITE, fontSize: 16, fontFamily: 'Inter_700Bold' }}>
                Mağazalar ({stores.length})
              </Text>
              {stores.map((store) => (
                <View
                  key={store.id}
                  style={{
                    flexDirection: 'row',
                    alignItems: 'center',
                    justifyContent: 'space-between',
                    paddingVertical: 10,
                    borderBottomWidth: 1,
                    borderBottomColor: '#334155',
                  }}
                >
                  <View style={{ gap: 2 }}>
                    <Text style={{ color: WHITE, fontSize: 14, fontFamily: 'Inter_600SemiBold', textTransform: 'capitalize' }}>
                      {store.store}
                    </Text>
                    {!store.in_stock && (
                      <Text style={{ color: '#EF4444', fontSize: 11 }}>Stokta yok</Text>
                    )}
                  </View>
                  <View style={{ alignItems: 'flex-end', gap: 2 }}>
                    <Text style={{ color: WHITE, fontSize: 15, fontFamily: 'Inter_700Bold' }}>
                      {fmt(store.current_price)}
                    </Text>
                    {store.discount_percent != null && store.discount_percent > 0 && (
                      <View style={{
                        backgroundColor: `${BRAND_GREEN}25`,
                        borderRadius: 6,
                        paddingHorizontal: 6,
                        paddingVertical: 2,
                      }}>
                        <Text style={{ color: BRAND_GREEN, fontSize: 11, fontFamily: 'Inter_600SemiBold' }}>
                          %{store.discount_percent} indirim
                        </Text>
                      </View>
                    )}
                  </View>
                </View>
              ))}
            </View>
          )}
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
            backgroundColor: BRAND_GREEN,
            borderRadius: 16,
            paddingVertical: 16,
            alignItems: 'center',
            flexDirection: 'row',
            justifyContent: 'center',
            gap: 8,
          }}
          onPress={() => alarmSheetRef.current?.expand()}
          activeOpacity={0.85}
        >
          <Ionicons name="hand-right" size={20} color={WHITE} />
          <Text style={{ color: WHITE, fontSize: 16, fontFamily: 'Inter_700Bold' }}>
            Talep Et
          </Text>
        </TouchableOpacity>
      </View>

      {/* Alarm/Talep kurma sheet */}
      <AlarmSetupSheet
        productId={product.id}
        currentPrice={currentPrice}
        sheetRef={alarmSheetRef}
      />
    </SafeAreaView>
  );
}
