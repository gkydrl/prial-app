import { useEffect, useRef } from 'react';
import { View, Animated } from 'react-native';

function SkeletonBox({ width, height, borderRadius = 6 }: { width: number | string; height: number; borderRadius?: number }) {
  const opacity = useRef(new Animated.Value(0.3)).current;

  useEffect(() => {
    Animated.loop(
      Animated.sequence([
        Animated.timing(opacity, { toValue: 0.7, duration: 700, useNativeDriver: true }),
        Animated.timing(opacity, { toValue: 0.3, duration: 700, useNativeDriver: true }),
      ])
    ).start();
  }, []);

  return (
    <Animated.View
      style={{
        width,
        height,
        borderRadius,
        backgroundColor: '#1E293B',
        opacity,
      }}
    />
  );
}

export function CardSkeleton() {
  return (
    <View
      style={{
        width: 160,
        height: 220,
        backgroundColor: '#0F172A',
        borderRadius: 12,
        overflow: 'hidden',
      }}
    >
      {/* Görsel alanı */}
      <SkeletonBox width="100%" height={130} borderRadius={0} />

      {/* İçerik */}
      <View style={{ padding: 8, gap: 6, flex: 1, justifyContent: 'center' }}>
        <SkeletonBox width="90%" height={11} />
        <SkeletonBox width="70%" height={11} />
        <SkeletonBox width="50%" height={14} borderRadius={4} />
      </View>
    </View>
  );
}

export function CardSkeletonRow({ count = 3 }: { count?: number }) {
  return (
    <View style={{ flexDirection: 'row', paddingHorizontal: 16, gap: 12 }}>
      {Array.from({ length: count }).map((_, i) => (
        <CardSkeleton key={i} />
      ))}
    </View>
  );
}
