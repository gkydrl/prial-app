import { useState } from 'react';
import { View, Text, ScrollView, Switch } from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';
import { router } from 'expo-router';
import { Button } from '@/components/ui/Button';
import { authApi } from '@/api/auth';
import { useAuthStore } from '@/store/authStore';
import { showAlert } from '@/store/alertStore';

export default function ConsentScreen() {
  const user = useAuthStore((s) => s.user);
  const updateUser = useAuthStore((s) => s.updateUser);
  const [loading, setLoading] = useState(false);

  const [prefs, setPrefs] = useState({
    push_notifications_enabled: false,
    email_notifications_enabled: false,
    notify_on_price_drop: false,
    notify_on_back_in_stock: false,
  });

  const toggle = (key: keyof typeof prefs) => {
    setPrefs((prev) => ({ ...prev, [key]: !prev[key] }));
  };

  const handleSave = async () => {
    setLoading(true);
    try {
      await authApi.saveConsent(prefs);
      updateUser({ ...prefs, has_completed_consent: true });
      router.replace('/(tabs)');
    } catch (e: any) {
      showAlert('Hata', e.response?.data?.detail ?? 'Tercihler kaydedilemedi');
    } finally {
      setLoading(false);
    }
  };

  const rows: { key: keyof typeof prefs; label: string; desc: string }[] = [
    {
      key: 'push_notifications_enabled',
      label: 'Anlık Bildirimler',
      desc: 'Fiyat düşüşü ve kampanya bildirimleri alın',
    },
    {
      key: 'email_notifications_enabled',
      label: 'E-posta Bildirimleri',
      desc: 'Haftalık fiyat raporu ve öneriler',
    },
    {
      key: 'notify_on_price_drop',
      label: 'Fiyat Düşüşü',
      desc: 'Takip ettiğiniz ürünlerde fiyat düştüğünde',
    },
    {
      key: 'notify_on_back_in_stock',
      label: 'Stok Bildirimi',
      desc: 'Tükenen ürünler tekrar satışa çıktığında',
    },
  ];

  return (
    <SafeAreaView style={{ flex: 1, backgroundColor: '#0A1628' }}>
      <ScrollView
        contentContainerStyle={{ flexGrow: 1, paddingHorizontal: 24, paddingVertical: 40, gap: 32 }}
      >
        {/* Header */}
        <View style={{ gap: 8 }}>
          <Text style={{ color: '#FFFFFF', fontSize: 28, fontFamily: 'Inter_700Bold' }}>
            Hoş geldin{user?.full_name ? `, ${user.full_name.split(' ')[0]}` : ''}!
          </Text>
          <Text style={{ color: '#94A3B8', fontSize: 15, lineHeight: 22 }}>
            İletişim tercihlerinizi belirleyin. Dilediğiniz zaman ayarlardan değiştirebilirsiniz.
          </Text>
        </View>

        {/* Preference toggles */}
        <View style={{ gap: 16 }}>
          {rows.map((row) => (
            <View
              key={row.key}
              style={{
                flexDirection: 'row',
                alignItems: 'center',
                justifyContent: 'space-between',
                backgroundColor: '#111D32',
                borderRadius: 12,
                padding: 16,
              }}
            >
              <View style={{ flex: 1, marginRight: 12 }}>
                <Text style={{ color: '#FFFFFF', fontSize: 15, fontFamily: 'Inter_600SemiBold' }}>
                  {row.label}
                </Text>
                <Text style={{ color: '#64748B', fontSize: 13, marginTop: 2 }}>{row.desc}</Text>
              </View>
              <Switch
                value={prefs[row.key]}
                onValueChange={() => toggle(row.key)}
                trackColor={{ false: '#334155', true: '#1D4ED8' }}
                thumbColor="#FFFFFF"
              />
            </View>
          ))}
        </View>

        {/* KVKK notice */}
        <Text style={{ color: '#64748B', fontSize: 12, lineHeight: 18 }}>
          6698 sayılı Kişisel Verilerin Korunması Kanunu kapsamında, kişisel verileriniz yalnızca
          hizmet sunumu amacıyla işlenmektedir. Tercihlerinizi istediğiniz zaman profil
          ayarlarından güncelleyebilirsiniz. Detaylı bilgi için{' '}
          <Text style={{ color: '#1D4ED8' }}>Gizlilik Politikası</Text>'nı inceleyebilirsiniz.
        </Text>

        {/* Continue button */}
        <Button onPress={handleSave} loading={loading}>
          Devam Et
        </Button>
      </ScrollView>
    </SafeAreaView>
  );
}
