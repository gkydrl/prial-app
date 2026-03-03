import { Modal, View, Text, TouchableOpacity } from 'react-native';
import { router } from 'expo-router';
import { Ionicons } from '@expo/vector-icons';
import { useAuthStore } from '@/store/authStore';

interface Props {
  visible: boolean;
  onDismiss: () => void;
}

export function OnboardingModal({ visible, onDismiss }: Props) {
  const completeOnboarding = useAuthStore((s) => s.completeOnboarding);

  const handleExplore = async () => {
    await completeOnboarding();
    onDismiss();
    router.push('/(tabs)/discover');
  };

  const handleSkip = async () => {
    await completeOnboarding();
    onDismiss();
  };

  return (
    <Modal
      visible={visible}
      transparent
      animationType="slide"
      statusBarTranslucent
      onRequestClose={handleSkip}
    >
      <View style={{ flex: 1, backgroundColor: 'rgba(0,0,0,0.7)', justifyContent: 'flex-end' }}>
        <View
          style={{
            backgroundColor: '#1A1A1A',
            borderTopLeftRadius: 24,
            borderTopRightRadius: 24,
            padding: 24,
            paddingBottom: 44,
            gap: 24,
          }}
        >
          {/* Handle */}
          <View
            style={{
              width: 40,
              height: 4,
              backgroundColor: '#3A3A3A',
              borderRadius: 2,
              alignSelf: 'center',
            }}
          />

          {/* İkon */}
          <View style={{ alignItems: 'center' }}>
            <View style={{
              width: 72,
              height: 72,
              borderRadius: 36,
              backgroundColor: '#1E293B',
              justifyContent: 'center',
              alignItems: 'center',
            }}>
              <Ionicons name="pricetag-outline" size={36} color="#1D4ED8" />
            </View>
          </View>

          {/* Başlık */}
          <View style={{ gap: 8, alignItems: 'center' }}>
            <Text style={{ color: '#FFFFFF', fontSize: 22, fontFamily: 'Inter_700Bold', textAlign: 'center' }}>
              Hoş geldin!
            </Text>
            <Text style={{ color: '#9CA3AF', fontSize: 15, lineHeight: 22, textAlign: 'center' }}>
              Takip etmek istediğin ürünleri keşfet ve talep oluştur.{'\n'}
              Fiyat düşünce seni haberdar edelim.
            </Text>
          </View>

          {/* Özellikler */}
          <View style={{ gap: 12 }}>
            {[
              { icon: 'search-outline', text: 'Ürün ara ve keşfet' },
              { icon: 'pricetag-outline', text: 'Talep oluştur, fiyat düşünce bildir' },
              { icon: 'trending-down-outline', text: 'Fiyat geçmişini takip et' },
            ].map((item) => (
              <View key={item.text} style={{ flexDirection: 'row', alignItems: 'center', gap: 12 }}>
                <View style={{
                  width: 36, height: 36, borderRadius: 10,
                  backgroundColor: '#262626',
                  justifyContent: 'center', alignItems: 'center',
                }}>
                  <Ionicons name={item.icon as any} size={18} color="#1D4ED8" />
                </View>
                <Text style={{ color: '#D1D5DB', fontSize: 14, fontFamily: 'Inter_400Regular', flex: 1 }}>
                  {item.text}
                </Text>
              </View>
            ))}
          </View>

          {/* Keşfet Butonu */}
          <TouchableOpacity
            onPress={handleExplore}
            style={{
              backgroundColor: '#1D4ED8',
              borderRadius: 14,
              paddingVertical: 16,
              alignItems: 'center',
            }}
          >
            <Text style={{ color: '#FFFFFF', fontSize: 16, fontFamily: 'Inter_700Bold' }}>
              Ürünleri Keşfet
            </Text>
          </TouchableOpacity>

          {/* Atla */}
          <TouchableOpacity onPress={handleSkip} style={{ alignItems: 'center' }}>
            <Text style={{ color: '#6B7280', fontSize: 14 }}>Şimdi değil, atla</Text>
          </TouchableOpacity>
        </View>
      </View>
    </Modal>
  );
}
