import React from 'react';
import { View, type ViewProps } from 'react-native';

export function Card({ className, children, ...props }: ViewProps) {
  return (
    <View
      className={`bg-card rounded-2xl overflow-hidden ${className ?? ''}`}
      style={{ shadowColor: '#000', shadowOffset: { width: 0, height: 2 }, shadowOpacity: 0.3, shadowRadius: 4, elevation: 4 }}
      {...props}
    >
      {children}
    </View>
  );
}
