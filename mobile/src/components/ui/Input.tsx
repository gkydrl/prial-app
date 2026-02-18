import React from 'react';
import { TextInput, View, Text, type TextInputProps } from 'react-native';

interface InputProps extends TextInputProps {
  label?: string;
  error?: string;
}

export function Input({ label, error, className, ...props }: InputProps) {
  return (
    <View className="gap-1.5">
      {label && <Text className="text-sm text-gray-300 font-medium">{label}</Text>}
      <TextInput
        className={`bg-surface border ${error ? 'border-danger' : 'border-border'} rounded-xl px-4 py-3.5 text-white text-base ${className ?? ''}`}
        placeholderTextColor="#6B7280"
        {...props}
      />
      {error && <Text className="text-xs text-danger">{error}</Text>}
    </View>
  );
}
