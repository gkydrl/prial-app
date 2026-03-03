import { useState } from 'react';
import { View, Text, TouchableOpacity } from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';
import { router } from 'expo-router';
import { Ionicons } from '@expo/vector-icons';
import { Input } from '@/components/ui/Input';
import { Button } from '@/components/ui/Button';
import { usersApi } from '@/api/users';
import { showAlert } from '@/store/alertStore';

const BG = '#0A1628';

export default function ChangePasswordScreen() {
  const [current, setCurrent] = useState('');
  const [next, setNext] = useState('');
  const [confirm, setConfirm] = useState('');
  const [loading, setLoading] = useState(false);

  const handleSave = async () => {
    if (!current || !next || !confirm) {
      showAlert('Hata', 'Tüm alanları doldurun.');
      return;
    }
    if (next.length < 8) {
      showAlert('Hata', 'Yeni şifre en az 8 karakter olmalı.');
      return;
    }
    if (next !== confirm) {
      showAlert('Hata', 'Yeni şifreler eşleşmiyor.');
      return;
    }
    setLoading(true);
    try {
      await usersApi.changePassword(current, next);
      showAlert('Başarılı', 'Şifreniz güncellendi.');
      router.back();
    } catch (e: any) {
      showAlert('Hata', e.response?.data?.detail ?? 'Şifre güncellenemedi.');
    } finally {
      setLoading(false);
    }
  };

  return (
    <SafeAreaView style={{ flex: 1, backgroundColor: BG }} edges={['top']}>
      {/* Header */}
      <View style={{ flexDirection: 'row', alignItems: 'center', gap: 12, paddingHorizontal: 16, paddingVertical: 14 }}>
        <TouchableOpacity onPress={() => router.back()} hitSlop={{ top: 8, bottom: 8, left: 8, right: 8 }}>
          <Ionicons name="arrow-back" size={22} color="#FFFFFF" />
        </TouchableOpacity>
        <Text style={{ color: '#FFFFFF', fontSize: 18, fontFamily: 'Inter_700Bold' }}>Şifre Değiştir</Text>
      </View>

      <View style={{ flex: 1, paddingHorizontal: 20, paddingTop: 24, gap: 16 }}>
        <Input
          label="Mevcut Şifre"
          value={current}
          onChangeText={setCurrent}
          secureTextEntry
          placeholder="Mevcut şifreniz"
        />
        <Input
          label="Yeni Şifre"
          value={next}
          onChangeText={setNext}
          secureTextEntry
          placeholder="En az 8 karakter"
        />
        <Input
          label="Yeni Şifre (Tekrar)"
          value={confirm}
          onChangeText={setConfirm}
          secureTextEntry
          placeholder="Yeni şifrenizi tekrar girin"
        />
        <Button onPress={handleSave} loading={loading}>
          Şifreyi Güncelle
        </Button>
      </View>
    </SafeAreaView>
  );
}
