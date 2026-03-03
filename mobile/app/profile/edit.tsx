import { useState } from 'react';
import { View, Text, TouchableOpacity, ActivityIndicator } from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';
import { router } from 'expo-router';
import { Ionicons } from '@expo/vector-icons';
import { Input } from '@/components/ui/Input';
import { Button } from '@/components/ui/Button';
import { usersApi } from '@/api/users';
import { useAuth } from '@/hooks/useAuth';
import { showAlert } from '@/store/alertStore';

const BG = '#0A1628';

export default function EditProfileScreen() {
  const { user, updateUser } = useAuth();
  const [fullName, setFullName] = useState(user?.full_name ?? '');
  const [loading, setLoading] = useState(false);

  const handleSave = async () => {
    setLoading(true);
    try {
      const { data } = await usersApi.updatePreferences({ full_name: fullName.trim() || null });
      updateUser(data);
      showAlert('Kaydedildi', 'Profil bilgileriniz güncellendi.');
      router.back();
    } catch {
      showAlert('Hata', 'Profil güncellenemedi, lütfen tekrar deneyin.');
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
        <Text style={{ color: '#FFFFFF', fontSize: 18, fontFamily: 'Inter_700Bold' }}>Profil Bilgileri</Text>
      </View>

      <View style={{ flex: 1, paddingHorizontal: 20, paddingTop: 24, gap: 20 }}>
        {/* E-posta (değiştirilemez) */}
        <View style={{ gap: 6 }}>
          <Text style={{ color: '#64748B', fontSize: 12, fontFamily: 'Inter_500Medium' }}>E-posta</Text>
          <View style={{
            backgroundColor: '#0F172A',
            borderRadius: 12,
            paddingHorizontal: 14,
            paddingVertical: 14,
          }}>
            <Text style={{ color: '#64748B', fontSize: 15, fontFamily: 'Inter_400Regular' }}>
              {user?.email}
            </Text>
          </View>
          <Text style={{ color: '#334155', fontSize: 11, fontFamily: 'Inter_400Regular' }}>
            E-posta adresi değiştirilemez
          </Text>
        </View>

        {/* Ad Soyad */}
        <Input
          label="Ad Soyad"
          value={fullName}
          onChangeText={setFullName}
          placeholder="Adın Soyadın"
          autoCapitalize="words"
        />

        <Button onPress={handleSave} loading={loading}>
          Kaydet
        </Button>
      </View>
    </SafeAreaView>
  );
}
