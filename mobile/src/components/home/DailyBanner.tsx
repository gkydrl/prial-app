import { useRef } from 'react';
import { View, Text, TouchableOpacity, ScrollView, Dimensions, NativeScrollEvent, NativeSyntheticEvent } from 'react-native';
import { Image } from 'expo-image';
import { LinearGradient } from 'expo-linear-gradient';
import { Ionicons } from '@expo/vector-icons';
import { router } from 'expo-router';
import { useAuthStore } from '@/store/authStore';
import { openAlarmSheet } from '@/store/alarmSheetStore';
import { showAlert } from '@/store/alertStore';
import { imageSource } from '@/utils/imageSource';
import { useState } from 'react';
import type { TopDropResponse } from '@/types/api';

const SCREEN_W = Dimensions.get('window').width;
const CARD_W = SCREEN_W - 32;

const LABELS = [
  { title: '🔥 Günün En İyi Fırsatı', sub: 'Bugün en çok düşen ürün' },
  { title: '⚡ Kaçırma! Büyük Düşüş', sub: 'Fiyat rekor kırdı' },
];

function fmt(n: number) {
  return Math.round(n).toLocaleString('tr-TR') + ' ₺';
}

function BannerCard({ item, index }: { item: TopDropResponse; index: number }) {
  const isAuthenticated = useAuthStore((s) => s.isAuthenticated);
  const { product, store, price_now, price_24h_ago, drop_amount, drop_percent } = item;
  const label = LABELS[index] ?? LABELS[0];

  const handleAlarm = () => {
    if (!isAuthenticated) {
      showAlert('Giriş Gerekli', 'Talep oluşturmak için giriş yapmalısınız.', [
        { text: 'Vazgeç', style: 'cancel' },
        { text: 'Giriş Yap', onPress: () => router.push('/(auth)/login') },
      ]);
      return;
    }
    openAlarmSheet({
      productId: product?.id ?? '',
      storeUrl: store?.url ?? null,
      currentPrice: price_now,
    });
  };

  if (price_now == null) return null;

  return (
    <TouchableOpacity
      activeOpacity={0.92}
      onPress={() => product?.id && router.push(`/product/${product.id}`)}
      style={{ width: CARD_W, marginHorizontal: 16 }}
    >
      <LinearGradient
        colors={['#0D2060', '#1A47C4']}
        start={{ x: 0, y: 0 }}
        end={{ x: 1, y: 1 }}
        style={{ borderRadius: 18, padding: 16, gap: 12 }}
      >
        {/* Üst etiket */}
        <View style={{ flexDirection: 'row', alignItems: 'center', justifyContent: 'space-between' }}>
          <View>
            <Text style={{ color: '#FFFFFF', fontSize: 15, fontFamily: 'Inter_700Bold' }}>
              {label.title}
            </Text>
            <Text style={{ color: '#93C5FD', fontSize: 11, fontFamily: 'Inter_400Regular', marginTop: 1 }}>
              {label.sub}
            </Text>
          </View>
          {!!drop_percent && (
            <View style={{
              backgroundColor: '#22C55E',
              borderRadius: 20,
              paddingHorizontal: 10,
              paddingVertical: 4,
            }}>
              <Text style={{ color: '#FFFFFF', fontSize: 12, fontFamily: 'Inter_700Bold' }}>
                %{Math.round(drop_percent)} ↘
              </Text>
            </View>
          )}
        </View>

        {/* İçerik */}
        <View style={{ flexDirection: 'row', gap: 14, alignItems: 'center' }}>
          {/* Ürün görseli */}
          <View style={{
            width: 90, height: 90,
            backgroundColor: '#FFFFFF',
            borderRadius: 14,
            overflow: 'hidden',
            flexShrink: 0,
          }}>
            <Image
              source={imageSource(product?.image_url)}
              style={{ width: '100%', height: '100%' }}
              contentFit="contain"
            />
          </View>

          {/* Metin */}
          <View style={{ flex: 1, gap: 6 }}>
            <Text
              style={{ color: '#FFFFFF', fontSize: 13, fontFamily: 'Inter_600SemiBold', lineHeight: 18 }}
              numberOfLines={2}
            >
              {product?.title ?? 'Ürün'}
            </Text>

            <View style={{ gap: 2 }}>
              {price_24h_ago != null && (
                <Text style={{ color: '#93C5FD', fontSize: 11, fontFamily: 'Inter_400Regular', textDecorationLine: 'line-through' }}>
                  {fmt(price_24h_ago)}
                </Text>
              )}
              <Text style={{ color: '#FFFFFF', fontSize: 20, fontFamily: 'Inter_700Bold' }}>
                {fmt(price_now)}
              </Text>
              {drop_amount != null && (
                <Text style={{ color: '#4ADE80', fontSize: 11, fontFamily: 'Inter_600SemiBold' }}>
                  ↘ {fmt(drop_amount)} daha ucuz
                </Text>
              )}
            </View>

            {/* CTA butonu */}
            <TouchableOpacity
              onPress={handleAlarm}
              activeOpacity={0.85}
              style={{
                flexDirection: 'row',
                alignItems: 'center',
                gap: 5,
                backgroundColor: '#FFFFFF1A',
                borderRadius: 10,
                paddingHorizontal: 10,
                paddingVertical: 6,
                alignSelf: 'flex-start',
                borderWidth: 1,
                borderColor: '#FFFFFF30',
              }}
            >
              <Ionicons name="pricetag-outline" size={12} color="#FFFFFF" />
              <Text style={{ color: '#FFFFFF', fontSize: 11, fontFamily: 'Inter_600SemiBold' }}>
                Talep Et
              </Text>
            </TouchableOpacity>
          </View>
        </View>
      </LinearGradient>
    </TouchableOpacity>
  );
}

export function DailyBanner({ items }: { items: TopDropResponse[] }) {
  const [activeIndex, setActiveIndex] = useState(0);
  const top2 = items.slice(0, 2);

  if (top2.length === 0) return null;

  const handleScroll = (e: NativeSyntheticEvent<NativeScrollEvent>) => {
    const x = e.nativeEvent.contentOffset.x;
    const index = Math.round(x / (CARD_W + 32));
    setActiveIndex(index);
  };

  return (
    <View style={{ marginTop: 8, marginBottom: 24 }}>
      <ScrollView
        horizontal
        pagingEnabled
        showsHorizontalScrollIndicator={false}
        onScroll={handleScroll}
        scrollEventThrottle={16}
        decelerationRate="fast"
        snapToInterval={CARD_W + 32}
        contentContainerStyle={{ gap: 0 }}
      >
        {top2.map((item, i) => (
          <BannerCard key={i} item={item} index={i} />
        ))}
      </ScrollView>

      {/* Dot indikatör */}
      {top2.length > 1 && (
        <View style={{ flexDirection: 'row', justifyContent: 'center', gap: 6, marginTop: 10 }}>
          {top2.map((_, i) => (
            <View
              key={i}
              style={{
                width: i === activeIndex ? 18 : 6,
                height: 6,
                borderRadius: 3,
                backgroundColor: i === activeIndex ? '#1D4ED8' : '#334155',
              }}
            />
          ))}
        </View>
      )}
    </View>
  );
}
