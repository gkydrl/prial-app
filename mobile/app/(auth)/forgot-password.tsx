import { useState } from 'react';
import { View, Text, TouchableOpacity, Image, ScrollView } from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';
import { router } from 'expo-router';
import { Ionicons } from '@expo/vector-icons';
import { Button } from '@/components/ui/Button';
import { Input } from '@/components/ui/Input';
import { authApi } from '@/api/auth';

const BG = '#0A1628';

export default function ForgotPasswordScreen() {
  const [email, setEmail] = useState('');
  const [loading, setLoading] = useState(false);
  const [sent, setSent] = useState(false);

  const handleSubmit = async () => {
    if (!email.trim()) return;
    setLoading(true);
    try {
      await authApi.forgotPassword(email.trim());
      setSent(true);
    } catch {
      // Hata olsa bile "gönderildi" göster — email enumeration önlemi
      setSent(true);
    } finally {
      setLoading(false);
    }
  };

  return (
    <SafeAreaView style={{ flex: 1, backgroundColor: BG }} edges={['top']}>
      <TouchableOpacity
        onPress={() => router.back()}
        style={{ paddingHorizontal: 16, paddingVertical: 12 }}
      >
        <Ionicons name="arrow-back" size={24} color="#FFFFFF" />
      </TouchableOpacity>

      <ScrollView
        contentContainerStyle={{ flexGrow: 1, justifyContent: 'center', paddingHorizontal: 24, gap: 32, paddingVertical: 40 }}
        keyboardShouldPersistTaps="handled"
      >
        <View style={{ alignItems: 'center', gap: 8 }}>
          <Image
            source={require('../../assets/images/logo.png')}
            style={{ width: 140, height: 56 }}
            resizeMode="contain"
          />
        </View>

        {sent ? (
          <View style={{ alignItems: 'center', gap: 16 }}>
            <View style={{ width: 72, height: 72, borderRadius: 36, backgroundColor: '#1D4ED820', justifyContent: 'center', alignItems: 'center' }}>
              <Ionicons name="mail-outline" size={36} color="#1D4ED8" />
            </View>
            <Text style={{ color: '#FFFFFF', fontSize: 18, fontFamily: 'Inter_700Bold', textAlign: 'center' }}>
              E-posta Gönderildi
            </Text>
            <Text style={{ color: '#64748B', fontSize: 14, fontFamily: 'Inter_400Regular', textAlign: 'center', lineHeight: 22 }}>
              Eğer bu adrese kayıtlı bir hesap varsa şifre sıfırlama bağlantısı gönderildi.{'\n'}
              Gelen kutunuzu kontrol edin.
            </Text>
            <Button onPress={() => router.replace('/(auth)/login')} style={{ marginTop: 8 }}>
              Giriş Yap
            </Button>
          </View>
        ) : (
          <View style={{ gap: 16 }}>
            <View style={{ gap: 6 }}>
              <Text style={{ color: '#FFFFFF', fontSize: 20, fontFamily: 'Inter_700Bold' }}>
                Şifreni Unuttun mu?
              </Text>
              <Text style={{ color: '#64748B', fontSize: 14, fontFamily: 'Inter_400Regular', lineHeight: 22 }}>
                E-posta adresini gir, sana şifre sıfırlama bağlantısı gönderelim.
              </Text>
            </View>
            <Input
              label="E-posta"
              value={email}
              onChangeText={setEmail}
              keyboardType="email-address"
              autoCapitalize="none"
              autoComplete="email"
              placeholder="ornek@email.com"
            />
            <Button onPress={handleSubmit} loading={loading} disabled={!email.trim()}>
              Bağlantı Gönder
            </Button>
          </View>
        )}
      </ScrollView>
    </SafeAreaView>
  );
}
