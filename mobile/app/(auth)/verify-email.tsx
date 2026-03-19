import { useState, useRef, useEffect } from 'react';
import { View, Text, TextInput, TouchableOpacity, ActivityIndicator } from 'react-native';
import { router } from 'expo-router';
import { authApi } from '@/api/auth';
import { useAuthStore } from '@/store/authStore';
import { showAlert } from '@/store/alertStore';

const CODE_LENGTH = 6;

export default function VerifyEmailScreen() {
  const [code, setCode] = useState('');
  const [loading, setLoading] = useState(false);
  const [resendCooldown, setResendCooldown] = useState(0);
  const inputRef = useRef<TextInput>(null);
  const user = useAuthStore((s) => s.user);
  const updateUser = useAuthStore((s) => s.updateUser);

  useEffect(() => {
    if (resendCooldown <= 0) return;
    const timer = setTimeout(() => setResendCooldown(resendCooldown - 1), 1000);
    return () => clearTimeout(timer);
  }, [resendCooldown]);

  const handleVerify = async () => {
    if (code.length !== CODE_LENGTH) {
      showAlert('Hata', '6 haneli doğrulama kodunu girin');
      return;
    }
    setLoading(true);
    try {
      await authApi.verifyEmail(code);
      updateUser({ is_verified: true });
      router.replace('/(tabs)');
    } catch (e: any) {
      const detail = e.response?.data?.detail;
      showAlert('Hata', typeof detail === 'string' ? detail : 'Doğrulama başarısız');
    } finally {
      setLoading(false);
    }
  };

  const handleResend = async () => {
    if (resendCooldown > 0) return;
    try {
      await authApi.resendVerification();
      setResendCooldown(60);
      showAlert('Kod Gönderildi', 'Yeni doğrulama kodu e-posta adresinize gönderildi.');
    } catch (e: any) {
      const detail = e.response?.data?.detail;
      showAlert('Hata', typeof detail === 'string' ? detail : 'Kod gönderilemedi');
    }
  };

  const handleCodeChange = (text: string) => {
    const cleaned = text.replace(/[^0-9]/g, '').slice(0, CODE_LENGTH);
    setCode(cleaned);
  };

  return (
    <View style={{ flex: 1, backgroundColor: '#0A1628', justifyContent: 'center', paddingHorizontal: 24 }}>
      <View style={{ gap: 8, marginBottom: 32, alignItems: 'center' }}>
        <Text style={{ color: '#FFFFFF', fontSize: 24, fontFamily: 'Inter_700Bold', textAlign: 'center' }}>
          E-posta Doğrulama
        </Text>
        <Text style={{ color: '#94A3B8', fontSize: 14, fontFamily: 'Inter_400Regular', textAlign: 'center' }}>
          {user?.email} adresine gönderilen{'\n'}6 haneli kodu girin
        </Text>
      </View>

      {/* Code input boxes */}
      <TouchableOpacity
        activeOpacity={1}
        onPress={() => inputRef.current?.focus()}
        style={{ flexDirection: 'row', justifyContent: 'center', gap: 8, marginBottom: 32 }}
      >
        {Array.from({ length: CODE_LENGTH }).map((_, i) => (
          <View
            key={i}
            style={{
              width: 48,
              height: 56,
              borderRadius: 12,
              borderWidth: 2,
              borderColor: code.length === i ? '#1D4ED8' : code[i] ? '#334155' : '#1E293B',
              backgroundColor: '#1E293B',
              justifyContent: 'center',
              alignItems: 'center',
            }}
          >
            <Text style={{ color: '#FFFFFF', fontSize: 24, fontFamily: 'Inter_700Bold' }}>
              {code[i] || ''}
            </Text>
          </View>
        ))}
      </TouchableOpacity>

      {/* Hidden input */}
      <TextInput
        ref={inputRef}
        value={code}
        onChangeText={handleCodeChange}
        keyboardType="number-pad"
        maxLength={CODE_LENGTH}
        autoFocus
        style={{ position: 'absolute', opacity: 0, height: 0 }}
      />

      {/* Verify button */}
      <TouchableOpacity
        onPress={handleVerify}
        disabled={loading || code.length !== CODE_LENGTH}
        activeOpacity={0.85}
        style={{
          backgroundColor: '#1D4ED8',
          borderRadius: 14,
          paddingVertical: 16,
          alignItems: 'center',
          opacity: loading || code.length !== CODE_LENGTH ? 0.5 : 1,
          marginBottom: 16,
        }}
      >
        {loading ? (
          <ActivityIndicator color="#fff" />
        ) : (
          <Text style={{ color: '#FFFFFF', fontSize: 16, fontFamily: 'Inter_700Bold' }}>
            Doğrula
          </Text>
        )}
      </TouchableOpacity>

      {/* Resend */}
      <TouchableOpacity onPress={handleResend} disabled={resendCooldown > 0} style={{ alignItems: 'center' }}>
        <Text style={{ color: resendCooldown > 0 ? '#64748B' : '#93C5FD', fontSize: 14, fontFamily: 'Inter_600SemiBold' }}>
          {resendCooldown > 0 ? `Tekrar gönder (${resendCooldown}s)` : 'Kodu tekrar gönder'}
        </Text>
      </TouchableOpacity>
    </View>
  );
}
