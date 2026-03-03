import React from 'react';
import { ActivityIndicator } from 'react-native';
import { Colors } from '@/constants/colors';
import { PrialLoader } from './PrialLoader';

export function LoadingSpinner({ full }: { full?: boolean }) {
  if (full) {
    return <PrialLoader />;
  }
  return <ActivityIndicator size="small" color={Colors.brand} />;
}
