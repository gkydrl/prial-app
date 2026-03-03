import { useState } from 'react';
import { View, Text, ScrollView, TouchableOpacity, Image } from 'react-native';
import { router, useLocalSearchParams } from 'expo-router';
import { showAlert } from '@/store/alertStore';
import { Button } from '@/components/ui/Button';
import { Input } from '@/components/ui/Input';
import { useAuth } from '@/hooks/useAuth';

export default function RegisterScreen() {
  const { returnProductId, openAlarm } = useLocalSearchParams<{
    returnProductId?: string;
    openAlarm?: string;
  }>();

  const [fullName, setFullName] = useState('');
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [loading, setLoading] = useState(false);
  const { register } = useAuth();

  const navigateAfterAuth = () => {
    if (returnProductId) {
      router.replace({
        pathname: '/product/[id]',
        params: { id: returnProductId, openAlarm: openAlarm ?? '' },
      });
    } else {
      router.replace('/(tabs)');
    }
  };

  const handleRegister = async () => {
    if (!email || !password) {
      showAlert('Hata', 'E-posta ve şifre gerekli');
      return;
    }
    if (password.length < 8) {
      showAlert('Hata', 'Şifre en az 8 karakter olmalı');
      return;
    }
    setLoading(true);
    try {
      await register(email.trim(), password, fullName.trim() || undefined);
      navigateAfterAuth();
    } catch (e: any) {
      showAlert('Kayıt Başarısız', e.response?.data?.detail ?? 'Kayıt oluşturulamadı');
    } finally {
      setLoading(false);
    }
  };

  return (
    <ScrollView
      style={{ flex: 1, backgroundColor: '#0A1628' }}
      contentContainerStyle={{ flexGrow: 1 }}
      keyboardShouldPersistTaps="handled"
    >
      <View className="flex-1 justify-center px-6 gap-8">
        <View className="items-center">
          <View
            style={{
              shadowColor: '#FFFFFF',
              shadowOffset: { width: 0, height: 0 },
              shadowOpacity: 0.35,
              shadowRadius: 28,
            }}
          >
            <Image
              source={require('../../assets/images/logo.png')}
              style={{ width: 180, height: 90 }}
              resizeMode="contain"
            />
          </View>
        </View>

        <View className="gap-4">
          <Text className="text-muted text-base text-center" style={{ marginBottom: 4 }}>Hesap oluştur</Text>
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
