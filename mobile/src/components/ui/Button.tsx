import React from 'react';
import { TouchableOpacity, Text, ActivityIndicator, type TouchableOpacityProps } from 'react-native';

type Variant = 'primary' | 'ghost' | 'danger';

interface ButtonProps extends TouchableOpacityProps {
  variant?: Variant;
  loading?: boolean;
  children: React.ReactNode;
}

const variantClasses: Record<Variant, { container: string; text: string }> = {
  primary: { container: 'bg-brand', text: 'text-white font-semibold' },
  ghost: { container: 'border border-brand', text: 'text-brand font-semibold' },
  danger: { container: 'bg-danger', text: 'text-white font-semibold' },
};

export function Button({ variant = 'primary', loading, disabled, children, className, ...props }: ButtonProps) {
  const { container, text } = variantClasses[variant];

  return (
    <TouchableOpacity
      className={`rounded-xl px-5 py-3.5 items-center justify-center flex-row gap-2 ${container} ${disabled || loading ? 'opacity-50' : ''} ${className ?? ''}`}
      disabled={disabled || loading}
      {...props}
    >
      {loading && <ActivityIndicator size="small" color="white" />}
      <Text className={`text-base ${text}`}>{children}</Text>
    </TouchableOpacity>
  );
}
