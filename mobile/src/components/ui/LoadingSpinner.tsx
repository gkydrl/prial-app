import React from 'react';
import { ActivityIndicator, View } from 'react-native';
import { Colors } from '@/constants/colors';

export function LoadingSpinner({ full }: { full?: boolean }) {
  if (full) {
    return (
      <View className="flex-1 items-center justify-center">
        <ActivityIndicator size="large" color={Colors.brand} />
      </View>
    );
  }
  return <ActivityIndicator size="small" color={Colors.brand} />;
}
