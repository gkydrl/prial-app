import React from 'react';
import { View, TextInput, TouchableOpacity } from 'react-native';
import { Ionicons } from '@expo/vector-icons';
import { Colors } from '@/constants/colors';

interface SearchBarProps {
  value: string;
  onChangeText: (t: string) => void;
  placeholder?: string;
  onFocus?: () => void;
  editable?: boolean;
}

export function SearchBar({ value, onChangeText, placeholder = 'Ürün ara...', onFocus, editable = true }: SearchBarProps) {
  return (
    <View className="flex-row items-center bg-surface border border-border rounded-xl px-4 gap-3 h-12">
      <Ionicons name="search-outline" size={18} color={Colors.muted} />
      <TextInput
        className="flex-1 text-white text-base"
        value={value}
        onChangeText={onChangeText}
        placeholder={placeholder}
        placeholderTextColor={Colors.muted}
        onFocus={onFocus}
        editable={editable}
      />
      {value.length > 0 && (
        <TouchableOpacity onPress={() => onChangeText('')}>
          <Ionicons name="close-circle" size={18} color={Colors.muted} />
        </TouchableOpacity>
      )}
    </View>
  );
}
