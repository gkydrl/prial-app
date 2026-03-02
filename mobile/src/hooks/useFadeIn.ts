import { useEffect } from 'react';
import { useSharedValue, withTiming, useAnimatedStyle } from 'react-native-reanimated';

export function useFadeIn(duration = 300) {
  const opacity = useSharedValue(0);

  useEffect(() => {
    opacity.value = withTiming(1, { duration });
  }, []);

  return useAnimatedStyle(() => ({ opacity: opacity.value }));
}
