import { useState } from 'react';
import { View, Text, ScrollView, Alert, TouchableOpacity } from 'react-native';
import { router } from 'expo-router';
import { Button } from '@/components/ui/Button';
import { Input } from '@/components/ui/Input';
import { useAuth } from '@/hooks/useAuth';

export default function LoginScreen() {
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [loading, setLoading] = useState(false);
  const { login } = useAuth();

  const handleLogin = async () => {
    if (!email || !password) {
      Alert.alert('Hata', 'E-posta ve şifre gerekli');
      return;
    }
    setLoading(true);
    try {
      await login(email.trim(), password);
      router.replace('/(tabs)');
    } catch (e: any) {
      Alert.alert('Giriş Başarısız', e.response?.data?.detail ?? 'E-posta veya şifre hatalı');
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
        {/* Logo */}
        <View className="items-center gap-2">
          <Text className="text-5xl font-bold text-brand">Prial</Text>
          <Text className="text-muted text-base">Fiyat takip ve alarm uygulaması</Text>
        </View>

        {/* Form */}
        <View className="gap-4">
          <Input
            label="E-posta"
            value={email}
            onChangeText={setEmail}
            keyboardType="email-address"
            autoCapitalize="none"
            autoComplete="email"
            placeholder="ornek@email.com"
          />
          <Input
            label="Şifre"
            value={password}
            onChangeText={setPassword}
            secureTextEntry
            placeholder="En az 8 karakter"
          />
          <Button onPress={handleLogin} loading={loading}>
            Giriş Yap
          </Button>
        </View>

        {/* Register link */}
        <TouchableOpacity
          className="items-center"
          onPress={() => router.push('/(auth)/register')}
        >
          <Text className="text-muted text-sm">
            Hesabın yok mu?{' '}
            <Text className="text-brand font-semibold">Kayıt ol</Text>
          </Text>
        </TouchableOpacity>
      </View>
    </ScrollView>
  );
}
