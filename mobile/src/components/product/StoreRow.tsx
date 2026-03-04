import React, { useState } from 'react';
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

function domainFromUrl(url: string): string | null {
  try {
    return new URL(url).hostname.replace(/^www\./, '');
  } catch {
    return null;
  }
}

function logoUrl(storeKey: string, storeUrl: string): string {
  const domain = STORE_DOMAINS[storeKey] ?? domainFromUrl(storeUrl);
  return `https://logo.clearbit.com/${domain ?? 'example.com'}`;
}

function storeLabel(storeKey: string, storeUrl: string): string {
  if (STORE_LABELS[storeKey] && storeKey !== 'other') return STORE_LABELS[storeKey];
  const domain = domainFromUrl(storeUrl);
  if (!domain) return storeKey;
  // "trendyol.com" → "Trendyol", "hepsiburada.com" → "Hepsiburada"
  const name = domain.split('.')[0];
  return name.charAt(0).toUpperCase() + name.slice(1);
}

export function StoreRow({ store }: { store: ProductStoreResponse }) {
  const logo = logoUrl(store.store, store.url);
  const label = storeLabel(store.store, store.url);
  const priceStr = store.current_price != null
    ? Math.round(Number(store.current_price)).toLocaleString('tr-TR') + ' ₺'
    : '-';
  const [logoError, setLogoError] = useState(false);

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
        {!logoError ? (
          <Image
            source={{ uri: logo }}
            style={{ width: 28, height: 28, borderRadius: 6 }}
            resizeMode="contain"
            onError={() => setLogoError(true)}
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
