import React from 'react';
import { View, Text, TouchableOpacity, Linking, Image } from 'react-native';
import { Ionicons } from '@expo/vector-icons';
import { Colors } from '@/constants/colors';
import type { ProductStoreResponse } from '@/types/api';

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

const STORE_LABELS: Record<string, string> = {
  trendyol:    'Trendyol',
  hepsiburada: 'Hepsiburada',
  amazon:      'Amazon',
  n11:         'N11',
  ciceksepeti: 'Çiçeksepeti',
  mediamarkt:  'MediaMarkt',
  teknosa:     'Teknosa',
  vatan:       'Vatan',
  other:       'Diğer',
};

function logoUrl(storeKey: string): string | null {
  const domain = STORE_DOMAINS[storeKey];
  if (!domain) return null;
  return `https://logo.clearbit.com/${domain}`;
}

export function StoreRow({ store }: { store: ProductStoreResponse }) {
  const logo = logoUrl(store.store);
  const label = STORE_LABELS[store.store] ?? store.store;
  const priceStr = store.current_price != null
    ? Math.round(Number(store.current_price)).toLocaleString('tr-TR') + ' ₺'
    : '-';

  return (
    <TouchableOpacity
      activeOpacity={0.7}
      onPress={() => Linking.openURL(store.url)}
      style={{
        flexDirection: 'row',
        alignItems: 'center',
        justifyContent: 'space-between',
        paddingVertical: 14,
        borderBottomWidth: 1,
        borderBottomColor: '#1E293B',
      }}
    >
      {/* Sol: Logo */}
      <View style={{ flexDirection: 'row', alignItems: 'center', gap: 10 }}>
        {logo ? (
          <Image
            source={{ uri: logo }}
            style={{ width: 28, height: 28, borderRadius: 6 }}
            resizeMode="contain"
          />
        ) : (
          <View style={{
            width: 28, height: 28, borderRadius: 6,
            backgroundColor: '#334155',
            justifyContent: 'center', alignItems: 'center',
          }}>
            <Ionicons name="storefront-outline" size={16} color="#94A3B8" />
          </View>
        )}
        <View style={{ gap: 2 }}>
          <Text style={{ color: '#FFFFFF', fontSize: 14, fontFamily: 'Inter_600SemiBold' }}>
            {label}
          </Text>
          {!store.in_stock && (
            <Text style={{ color: '#F59E0B', fontSize: 11, fontFamily: 'Inter_400Regular' }}>
              Stokta yok
            </Text>
          )}
        </View>
      </View>

      {/* Sağ: Fiyat + ok */}
      <View style={{ flexDirection: 'row', alignItems: 'center', gap: 6 }}>
        <Text style={{ color: '#FFFFFF', fontSize: 15, fontFamily: 'Inter_700Bold' }}>
          {priceStr}
        </Text>
        <Ionicons name="chevron-forward" size={16} color="#475569" />
      </View>
    </TouchableOpacity>
  );
}
