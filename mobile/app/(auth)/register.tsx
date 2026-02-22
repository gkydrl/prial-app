import { useState } from 'react';
import { View, Text, ScrollView, Alert, TouchableOpacity } from 'react-native';
import { router } from 'expo-router';
import { Button } from '@/components/ui/Button';
import { Input } from '@/components/ui/Input';
import { useAuth } from '@/hooks/useAuth';

export default function RegisterScreen() {
  const [fullName, setFullName] = useState('');
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [loading, setLoading] = useState(false);
  const { register } = useAuth();

  const handleRegister = async () => {
    if (!email || !password) {
      Alert.alert('Hata', 'E-posta ve şifre gerekli');
      return;
    }
    if (password.length < 8) {
      Alert.alert('Hata', 'Şifre en az 8 karakter olmalı');
      return;
    }
    setLoading(true);
    try {
      await register(email.trim(), password, fullName.trim() || undefined);
      router.replace('/(auth)/onboarding');
    } catch (e: any) {
      Alert.alert('Kayıt Başarısız', e.response?.data?.detail ?? 'Kayıt oluşturulamadı');
    } finally {
      setLoading(false);
    }
  };

  return (
    <ScrollView
      className="flex-1 bg-background"
      contentContainerStyle={{ flexGrow: 1 }}
      keyboardShouldPersistTaps="handled"
    >
      <View className="flex-1 justify-center px-6 gap-8">
        <View className="items-center gap-2">
          <Text className="text-5xl font-bold text-brand">Prial</Text>
          <Text className="text-muted text-base">Hesap oluştur</Text>
        </View>

        <View className="gap-4">
          <Input
            label="Ad Soyad (isteğe bağlı)"
            value={fullName}
            onChangeText={setFullName}
            placeholder="Adın Soyadın"
          />
          <Input
            label="E-posta"
            value={email}
            onChangeText={setEmail}
            keyboardType="email-address"
            autoCapitalize="none"
            placeholder="ornek@email.com"
          />
          <Input
            label="Şifre"
            value={password}
            onChangeText={setPassword}
            secureTextEntry
            placeholder="En az 8 karakter"
          />
          <Button onPress={handleRegister} loading={loading}>
            Kayıt Ol
          </Button>
        </View>

        <TouchableOpacity className="items-center" onPress={() => router.back()}>
          <Text className="text-muted text-sm">
            Zaten hesabın var mı? <Text className="text-brand font-semibold">Giriş yap</Text>
          </Text>
        </TouchableOpacity>
      </View>
    </ScrollView>
  );
}
