import { View, Text, Image } from 'react-native';
import { Ionicons } from '@expo/vector-icons';
import { SignalBadge } from '@/components/ui/SignalBadge';
import type { ProductResponse } from '@/types/api';

const CARD = '#1E293B';
const WHITE = '#FFFFFF';
const MUTED = '#CBD5E1';

interface PrialSaysProps {
  product: ProductResponse;
  bestPrice: number | null;
}

function extractSummary(text: string): string {
  if (text.trimStart().startsWith('{')) {
    try {
      const parsed = JSON.parse(text);
      return parsed.summary || text;
    } catch {
      const match = text.match(/"summary"\s*:\s*"([^"]+)"/);
      if (match) return match[1];
    }
  }
  return text;
}

function buildPrialParagraph(product: ProductResponse, bestPrice: number | null): string {
  const parts: string[] = [];

  if (product.reasoning_text) {
    const text = extractSummary(product.reasoning_text);
    if (text) parts.push(text);
  }

  if (product.reasoning_pros && product.reasoning_pros.length > 0) {
    const prosText =
      product.reasoning_pros.length === 1
        ? product.reasoning_pros[0]
        : `${product.reasoning_pros[0]} ve ${product.reasoning_pros[1]}`;
    parts.push(`Özellikle ${prosText} önemli avantajlar.`);
  }

  if (product.reasoning_cons && product.reasoning_cons.length > 0) {
    parts.push(`Öte yandan, ${product.reasoning_cons[0]} konusunda dikkatli olunmalı.`);
  }

  if (bestPrice && product.l1y_lowest_price) {
    const diff = bestPrice - product.l1y_lowest_price;
    const pct = (diff / product.l1y_lowest_price) * 100;
    if (pct <= 5) {
      parts.push('Mevcut fiyat son 1 yılın en düşüğüne oldukça yakın.');
    } else if (pct <= 15) {
      parts.push(`Mevcut fiyat son 1 yılın en düşüğünden %${Math.round(pct)} daha yüksek.`);
    }
  }

  if (product.recommendation === 'IYI_FIYAT') {
    parts.push('Şimdi alabilirsiniz.');
  } else if (product.recommendation === 'FIYAT_DUSEBILIR') {
    parts.push('Biraz beklemenizi öneriyoruz.');
  } else if (product.recommendation === 'FIYAT_YUKSELISTE') {
    parts.push('Fiyat yükselişte, kaçırmayın.');
  }

  return parts.join(' ');
}

export function PrialSays({ product, bestPrice }: PrialSaysProps) {
  const rec = product.recommendation;

  if (!rec) {
    return (
      <View style={{ backgroundColor: CARD, borderRadius: 16, padding: 16, flexDirection: 'row', alignItems: 'center', gap: 12 }}>
        <View style={{ width: 40, height: 40, borderRadius: 20, backgroundColor: '#334155', justifyContent: 'center', alignItems: 'center' }}>
          <Ionicons name="bulb-outline" size={20} color="#64748B" />
        </View>
        <View style={{ flex: 1 }}>
          <Text style={{ color: WHITE, fontSize: 14, fontFamily: 'Inter_600SemiBold' }}>
            AI Analizi Bekleniyor
          </Text>
          <Text style={{ color: '#64748B', fontSize: 12, fontFamily: 'Inter_400Regular' }}>
            Bu ürün için tahmin henüz oluşturulmadı.
          </Text>
        </View>
      </View>
    );
  }

  const paragraph = buildPrialParagraph(product, bestPrice);
  const pros = product.reasoning_pros ?? [];
  const cons = product.reasoning_cons ?? [];

  return (
    <View style={{ backgroundColor: CARD, borderRadius: 16, padding: 16, gap: 12 }}>
      {/* Header */}
      <View style={{ flexDirection: 'row', alignItems: 'center', justifyContent: 'space-between' }}>
        <View style={{ flexDirection: 'row', alignItems: 'center', gap: 6 }}>
          <Image
            source={require('../../../assets/images/logo.png')}
            style={{ height: 20, width: 60 }}
            resizeMode="contain"
          />
          <Text style={{ color: WHITE, fontSize: 16, fontFamily: 'Inter_700Bold' }}>
            Yorumu:
          </Text>
        </View>
        <SignalBadge recommendation={rec} size="md" />
      </View>

      {/* Reasoning paragraph */}
      {paragraph ? (
        <Text style={{ color: MUTED, fontSize: 13, fontFamily: 'Inter_400Regular', lineHeight: 20 }}>
          {paragraph}
        </Text>
      ) : null}

      {/* Pros */}
      {pros.length > 0 && (
        <View style={{ gap: 6 }}>
          {pros.map((pro, i) => (
            <View key={i} style={{ flexDirection: 'row', alignItems: 'flex-start', gap: 8 }}>
              <Ionicons name="checkmark-circle" size={16} color="#86EFAC" style={{ marginTop: 2 }} />
              <Text style={{ color: '#86EFAC', fontSize: 12, fontFamily: 'Inter_400Regular', flex: 1 }}>
                {pro}
              </Text>
            </View>
          ))}
        </View>
      )}

      {/* Cons */}
      {cons.length > 0 && (
        <View style={{ gap: 6 }}>
          {cons.map((con, i) => (
            <View key={i} style={{ flexDirection: 'row', alignItems: 'flex-start', gap: 8 }}>
              <Ionicons name="warning" size={16} color="#FCD34D" style={{ marginTop: 2 }} />
              <Text style={{ color: '#FCD34D', fontSize: 12, fontFamily: 'Inter_400Regular', flex: 1 }}>
                {con}
              </Text>
            </View>
          ))}
        </View>
      )}

      {/* 1Y comparison */}
      {bestPrice != null && product.l1y_lowest_price != null && product.l1y_lowest_price < bestPrice && (
        <View style={{ backgroundColor: '#0F172A', borderRadius: 8, padding: 10 }}>
          <Text style={{ color: '#94A3B8', fontSize: 11, fontFamily: 'Inter_400Regular' }}>
            Son 1 yılın en düşüğü: {Math.round(product.l1y_lowest_price).toLocaleString('tr-TR')} TL
            {' '}(%{Math.round(((bestPrice - product.l1y_lowest_price) / product.l1y_lowest_price) * 100)} daha yüksek)
          </Text>
        </View>
      )}
    </View>
  );
}
