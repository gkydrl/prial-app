import { View, Text, TouchableOpacity } from 'react-native';

interface SectionHeaderProps {
  title: string;
  subtitle?: string;
  onSeeAll?: () => void;
}

export function SectionHeader({ title, subtitle, onSeeAll }: SectionHeaderProps) {
  return (
    <View
      style={{
        flexDirection: 'row',
        alignItems: 'flex-start',
        justifyContent: 'space-between',
        paddingHorizontal: 16,
        marginBottom: 12,
      }}
    >
      {/* Sol: dikey çizgi + başlık + alt başlık */}
      <View style={{ flexDirection: 'row', alignItems: 'center', gap: 8 }}>
        <View style={{ width: 3, height: 40, borderRadius: 2, backgroundColor: '#1D4ED8' }} />
        <View style={{ gap: 2 }}>
          <Text style={{ color: '#FFFFFF', fontSize: 20, fontFamily: 'Inter_700Bold' }}>
            {title}
          </Text>
          {subtitle && (
            <Text style={{ color: '#6B7280', fontSize: 12, fontFamily: 'Inter_400Regular' }}>
              {subtitle}
            </Text>
          )}
        </View>
      </View>

      {/* Sağ: Tümünü Gör */}
      {onSeeAll && (
        <TouchableOpacity onPress={onSeeAll} style={{ paddingTop: 2 }}>
          <Text style={{ color: '#1D4ED8', fontSize: 14, fontFamily: 'Inter_500Medium' }}>
            Tümünü Gör →
          </Text>
        </TouchableOpacity>
      )}
    </View>
  );
}
