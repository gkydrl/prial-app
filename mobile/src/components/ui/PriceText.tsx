import React from 'react';
import { Text, type TextProps } from 'react-native';
import { formatTRY } from '@/utils/currency';

interface PriceTextProps extends TextProps {
  value: number | null | undefined;
  size?: 'sm' | 'md' | 'lg' | 'xl';
  dimmed?: boolean;
  strikethrough?: boolean;
}

const sizeClasses = { sm: 'text-sm', md: 'text-base', lg: 'text-xl', xl: 'text-3xl' };

export function PriceText({ value, size = 'md', dimmed, strikethrough, className, ...props }: PriceTextProps) {
  return (
    <Text
      className={`font-bold ${sizeClasses[size]} ${dimmed ? 'text-muted line-through' : 'text-white'} ${strikethrough ? 'line-through' : ''} ${className ?? ''}`}
      {...props}
    >
      {formatTRY(value)}
    </Text>
  );
}
