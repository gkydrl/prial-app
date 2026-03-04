import { useState, useEffect } from 'react';
import { View, Text, TouchableOpacity, Image, ScrollView } from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';
import { router, useLocalSearchParams } from 'expo-router';
import { Ionicons } from '@expo/vector-icons';
import { Button } from '@/components/ui/Button';
import { Input } from '@/components/ui/Input';
import { authApi } from '@/api/auth';
import { showAlert } from '@/store/alertStore';

const BG = '#0A1628';

export default function ResetPasswordScreen() {
  const { token } = useLocalSearchParams<{ token?: string }>();
  const [password, setPassword] = useState('');
  const [confirm, setConfirm] = useState('');
  const [loading, setLoading] = useState(false);
  const [done, setDone] = useState(false);

  const handleReset = async () => {
    if (password.length < 8) {
      showAlert('Hata', 'Şifre en az 8 karakter olmalı');
      return;
    }
    if (password !== confirm) {
      showAlert('Hata', 'Şifreler eşleşmiyor');
      return;
    }
    if (!token) {
      showAlert('Hata', 'Geçersiz bağlantı');
      return;
    }
    setLoading(true);
    try {
      await authApi.resetPassword(token, password);
      setDone(true);
    } catch (e: any) {
      showAlert('Hata', e.response?.data?.detail ?? 'Geçersiz veya süresi dolmuş bağlantı');
    } finally {
      setLoading(false);
    }
  };

  if (!token) {
    return (
      <SafeAreaView style={{ flex: 1, backgroundColor: BG, justifyContent: 'center', alignItems: 'center', gap: 16 }} edges={['top']}>
        <Ionicons name="close-circle-outline" size={52} color="#EF4444" />
        <Text style={{ color: '#FFFFFF', fontSize: 16, fontFamily: 'Inter_600SemiBold' }}>Geçersiz bağlantı</Text>
        <TouchableOpacity onPress={() => router.replace('/(auth)/login')}>
          <Text style={{ color: '#1D4ED8', fontFamily: 'Inter_600SemiBold' }}>Giriş sayfasına dön</Text>
        </TouchableOpacity>
      </SafeAreaView>
    );
  }

  return (
    <SafeAreaView style={{ flex: 1, backgroundColor: BG }} edges={['top']}>
      <TouchableOpacity
        onPress={() => router.replace('/(auth)/login')}
        style={{ paddingHorizontal: 16, paddingVertical: 12 }}
      >
        <Ionicons name="arrow-back" size={24} color="#FFFFFF" />
      </TouchableOpacity>

      <ScrollView
        contentContainerStyle={{ flexGrow: 1, justifyContent: 'center', paddingHorizontal: 24, gap: 32, paddingVertical: 40 }}
        keyboardShouldPersistTaps="handled"
      >
        <View style={{ alignItems: 'center' }}>
          <Image
            source={require('../../assets/images/logo.png')}
            style={{ width: 140, height: 56 }}
            resizeMode="contain"
          />
        </View>

        {done ? (
          <View style={{ alignItems: 'center', gap: 16 }}>
            <View style={{ width: 72, height: 72, borderRadius: 36, backgroundColor: '#22C55E20', justifyContent: 'center', alignItems: 'center' }}>
              <Ionicons name="checkmark-circle-outline" size={40} color="#22C55E" />
            </View>
            <Text style={{ color: '#FFFFFF', fontSize: 18, fontFamily: 'Inter_700Bold', textAlign: 'center' }}>
              Şifre Güncellendi
            </Text>
            <Text style={{ color: '#64748B', fontSize: 14, fontFamily: 'Inter_400Regular', textAlign: 'center' }}>
              Yeni şifrenle giriş yapabilirsin.
            </Text>
            <Button onPress={() => router.replace('/(auth)/login')} style={{ marginTop: 8 }}>
              Giriş Yap
            </Button>
          </View>
        ) : (
          <View style={{ gap: 16 }}>
            <View style={{ gap: 6 }}>
              <Text style={{ color: '#FFFFFF', fontSize: 20, fontFamily: 'Inter_700Bold' }}>
                Yeni Şifre Belirle
              </Text>
              <Text style={{ color: '#64748B', fontSize: 14, fontFamily: 'Inter_400Regular' }}>
                En az 8 karakter kullan.
              </Text>
            </View>
            <Input
              label="Yeni Şifre"
              value={password}
              onChangeText={setPassword}
              secureTextEntry
              placeholder="En az 8 karakter"
            />
            <Input
              label="Şifre Tekrar"
              value={confirm}
              onChangeText={setConfirm}
              secureTextEntry
              placeholder="Şifreyi tekrar gir"
            />
            <Button
              onPress={handleReset}
              loading={loading}
              disabled={!password || !confirm}
            >
              Şifremi Sıfırla
            </Button>
          </View>
        )}
      </ScrollView>
    </SafeAreaView>
  );
}
