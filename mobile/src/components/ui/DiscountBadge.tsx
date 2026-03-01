import { View, Text } from 'react-native';

interface DiscountBadgeProps {
  percent: number;
}

export function DiscountBadge({ percent }: DiscountBadgeProps) {
  return (
    <View
      style={{
        position: 'absolute',
        top: 8,
        left: 8,
        backgroundColor: '#22C55E',
        borderRadius: 20,
        paddingHorizontal: 8,
        paddingVertical: 4,
      }}
    >
      <Text style={{ color: '#FFFFFF', fontSize: 11, fontFamily: 'Inter_700Bold' }}>
        ↘ -{percent.toFixed(1)}%
      </Text>
    </View>
  );
}
