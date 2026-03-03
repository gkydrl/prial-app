import { useState, useEffect, useCallback, useRef } from 'react';
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
import { PrialLoader } from '@/components/ui/PrialLoader';
import client from '@/api/client';
import { ENDPOINTS } from '@/constants/api';
import type { ProductResponse } from '@/types/api';

const BG = '#0A1628';
const CARD = '#1E293B';
const MUTED = '#64748B';

const fmtPrice = (price: number | null | undefined) =>
  price != null ? Math.round(price).toLocaleString('tr-TR') + ' ₺' : '-';

function ProductRow({ product }: { product: ProductResponse }) {
  const store = product.stores?.[0];
  const price = store?.current_price;
  const discount = store?.discount_percent;

  return (
    <TouchableOpacity
      activeOpacity={0.8}
      onPress={() => router.push(`/product/${product.id}`)}
      style={{
        flexDirection: 'row',
        alignItems: 'center',
        backgroundColor: CARD,
        borderRadius: 14,
        padding: 12,
        gap: 12,
        marginBottom: 8,
      }}
    >
      {/* Görsel */}
      <View style={{ width: 60, height: 60, borderRadius: 10, overflow: 'hidden', backgroundColor: '#2D3F55' }}>
        {product.image_url ? (
          <Image
            source={{ uri: product.image_url }}
            style={{ width: 60, height: 60 }}
            contentFit="contain"
          />
        ) : (
          <View style={{ flex: 1, justifyContent: 'center', alignItems: 'center' }}>
            <Ionicons name="cube-outline" size={28} color="#475569" />
          </View>
        )}
      </View>

      {/* Bilgi */}
      <View style={{ flex: 1, gap: 4 }}>
        <Text
          style={{ color: '#FFFFFF', fontSize: 13, fontFamily: 'Inter_600SemiBold', lineHeight: 18 }}
          numberOfLines={2}
        >
          {product.title}
        </Text>
        <View style={{ flexDirection: 'row', alignItems: 'center', gap: 8 }}>
          <Text style={{ color: '#FFFFFF', fontSize: 15, fontFamily: 'Inter_700Bold' }}>
            {fmtPrice(price)}
          </Text>
          {!!discount && (
            <View style={{
              backgroundColor: '#22C55E20',
              borderRadius: 4,
              paddingHorizontal: 5,
              paddingVertical: 1,
            }}>
              <Text style={{ color: '#22C55E', fontSize: 10, fontFamily: 'Inter_700Bold' }}>
                -{discount}%
              </Text>
            </View>
          )}
          {product.alarm_count > 0 && (
            <View style={{ flexDirection: 'row', alignItems: 'center', gap: 3, marginLeft: 'auto' }}>
              <Ionicons name="pricetag-outline" size={11} color="#A78BFA" />
              <Text style={{ color: '#A78BFA', fontSize: 11, fontFamily: 'Inter_600SemiBold' }}>
                {product.alarm_count.toLocaleString('tr-TR')} talep
              </Text>
            </View>
          )}
        </View>
      </View>

      {/* Ok */}
      <Ionicons name="chevron-forward" size={18} color="#334155" />
    </TouchableOpacity>
  );
}

export default function AlarmSearchScreen() {
  const [query, setQuery] = useState('');
  const [results, setResults] = useState<ProductResponse[]>([]);
  const [isLoading, setIsLoading] = useState(false);
  const [hasSearched, setHasSearched] = useState(false);
  const inputRef = useRef<TextInput>(null);

  // Ekran açılınca input'a odaklan
  useEffect(() => {
    const t = setTimeout(() => inputRef.current?.focus(), 150);
    return () => clearTimeout(t);
  }, []);

  const search = useCallback(async (q: string) => {
    if (!q.trim()) {
      setResults([]);
      setHasSearched(false);
      return;
    }
    setIsLoading(true);
    setHasSearched(true);
    try {
      const res = await client.get<ProductResponse[]>(ENDPOINTS.DISCOVER_SEARCH, {
        params: { q: q.trim(), limit: 30 },
      });
      setResults(res.data);
    } catch {
      setResults([]);
    } finally {
      setIsLoading(false);
    }
  }, []);

  // Debounce
  useEffect(() => {
    const t = setTimeout(() => search(query), 400);
    return () => clearTimeout(t);
  }, [query]);

  return (
    <SafeAreaView style={{ flex: 1, backgroundColor: BG }} edges={['top']}>
      {/* Header */}
      <View style={{
        flexDirection: 'row',
        alignItems: 'center',
        paddingHorizontal: 16,
        paddingTop: 14,
        paddingBottom: 12,
        gap: 12,
      }}>
        <TouchableOpacity
          onPress={() => router.back()}
          hitSlop={{ top: 8, bottom: 8, left: 8, right: 8 }}
        >
          <Ionicons name="close" size={24} color="#FFFFFF" />
        </TouchableOpacity>
        <Text style={{ color: '#FFFFFF', fontSize: 18, fontFamily: 'Inter_700Bold' }}>
          Talep Oluştur
        </Text>
      </View>

      {/* Arama kutusu */}
      <View style={{
        flexDirection: 'row',
        alignItems: 'center',
        backgroundColor: CARD,
        borderRadius: 14,
        marginHorizontal: 16,
        marginBottom: 16,
        paddingHorizontal: 14,
        gap: 10,
      }}>
        <Ionicons name="search-outline" size={18} color={MUTED} />
        <TextInput
          ref={inputRef}
          value={query}
          onChangeText={setQuery}
          placeholder="Ürün veya marka ara..."
          placeholderTextColor="#475569"
          style={{
            flex: 1,
            color: '#FFFFFF',
            fontSize: 15,
            fontFamily: 'Inter_400Regular',
            paddingVertical: 14,
          }}
          autoCapitalize="none"
          returnKeyType="search"
          clearButtonMode="while-editing"
        />
        {query.length > 0 && (
          <TouchableOpacity onPress={() => setQuery('')}>
            <Ionicons name="close-circle" size={18} color="#475569" />
          </TouchableOpacity>
        )}
      </View>

      {/* Sonuçlar */}
      {isLoading ? (
        <PrialLoader />
      ) : !hasSearched ? (
        <View style={{ flex: 1, justifyContent: 'center', alignItems: 'center', gap: 12, paddingBottom: 60 }}>
          <Ionicons name="search-outline" size={48} color="#1E293B" />
          <Text style={{ color: MUTED, fontSize: 14, fontFamily: 'Inter_400Regular' }}>
            Takip etmek istediğin ürünü ara
          </Text>
        </View>
      ) : results.length === 0 ? (
        <View style={{ flex: 1, justifyContent: 'center', alignItems: 'center', gap: 12, paddingBottom: 60 }}>
          <Ionicons name="cube-outline" size={48} color="#1E293B" />
          <Text style={{ color: MUTED, fontSize: 14, fontFamily: 'Inter_400Regular' }}>
            Ürün bulunamadı
          </Text>
        </View>
      ) : (
        <FlatList
          data={results}
          keyExtractor={(item) => item.id}
          renderItem={({ item }) => <ProductRow product={item} />}
          showsVerticalScrollIndicator={false}
          contentContainerStyle={{ paddingHorizontal: 16, paddingBottom: 100 }}
          keyboardShouldPersistTaps="handled"
        />
      )}
    </SafeAreaView>
  );
}
