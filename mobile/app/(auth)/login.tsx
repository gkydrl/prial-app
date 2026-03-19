import { useState } from 'react';
import { View, Text, ScrollView, TouchableOpacity, Image } from 'react-native';
import { showAlert } from '@/store/alertStore';
import { SafeAreaView, useSafeAreaInsets } from 'react-native-safe-area-context';
import { Ionicons } from '@expo/vector-icons';
import { router } from 'expo-router';
import { Button } from '@/components/ui/Button';
import { Input } from '@/components/ui/Input';
import { useAuth } from '@/hooks/useAuth';
import { useAuthStore } from '@/store/authStore';

export default function LoginScreen() {
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [loading, setLoading] = useState(false);
  const { login } = useAuth();
  const insets = useSafeAreaInsets();

  const handleLogin = async () => {
    if (!email || !password) {
      showAlert('Hata', 'E-posta ve şifre gerekli');
      return;
    }
    setLoading(true);
    try {
      await login(email.trim(), password);
      // Check if user is verified after login
      const user = useAuthStore.getState().user;
      if (user && !user.is_verified) {
        router.replace('/(auth)/verify-email');
      } else {
        router.replace('/(tabs)');
      }
    } catch (e: any) {
      showAlert('Giriş Başarısız', e.response?.data?.detail ?? 'E-posta veya şifre hatalı');
    } finally {
      setLoading(false);
    }
  };

  return (
    <SafeAreaView style={{ flex: 1, backgroundColor: '#0A1628' }} edges={[]}>
      <ScrollView
        style={{ flex: 1 }}
        contentContainerStyle={{ flexGrow: 1 }}
        keyboardShouldPersistTaps="handled"
      >
        <View style={{ flex: 1, justifyContent: 'center', paddingHorizontal: 24, gap: 32, paddingVertical: 40 }}>
          {/* Logo */}
          <View style={{ alignItems: 'center', gap: 8 }}>
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
            <Text style={{ color: '#FFFFFF', fontSize: 16 }}>Fiyat Talep Platformu</Text>
          </View>

          {/* Form */}
          <View style={{ gap: 16 }}>
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
            <TouchableOpacity
              style={{ alignItems: 'center' }}
              onPress={() => router.push('/(auth)/forgot-password')}
            >
              <Text style={{ color: '#1D4ED8', fontSize: 13, fontFamily: 'Inter_400Regular' }}>
                Şifremi Unuttum
              </Text>
            </TouchableOpacity>
          </View>

          {/* Register link */}
          <TouchableOpacity
            style={{ alignItems: 'center' }}
            onPress={() => router.push('/(auth)/register')}
          >
            <Text style={{ color: '#6B7280', fontSize: 14 }}>
              Hesabın yok mu?{' '}
              <Text style={{ color: '#1D4ED8', fontFamily: 'Inter_600SemiBold' }}>Kayıt ol</Text>
            </Text>
          </TouchableOpacity>
        </View>
      </ScrollView>

      {/* Guest link — ekranın en altında */}
      <TouchableOpacity
        onPress={() => router.replace('/(tabs)')}
        style={{
          flexDirection: 'row',
          alignItems: 'center',
          justifyContent: 'center',
          gap: 4,
          paddingTop: 16,
          paddingBottom: insets.bottom + 16,
        }}
      >
        <Text style={{ color: '#64748B', fontSize: 14, fontFamily: 'Inter_400Regular' }}>
          Üye olmadan devam et
        </Text>
        <Ionicons name="chevron-forward" size={16} color="#64748B" />
      </TouchableOpacity>
    </SafeAreaView>
  );
}
