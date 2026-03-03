import { View, Text, TouchableOpacity, Linking, Image } from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';
import { router } from 'expo-router';
import { Ionicons } from '@expo/vector-icons';

const BG = '#0A1628';
const CARD = '#1E293B';

function LinkRow({ icon, label, url }: { icon: React.ComponentProps<typeof Ionicons>['name']; label: string; url: string }) {
  return (
    <TouchableOpacity
      onPress={() => Linking.openURL(url)}
      activeOpacity={0.7}
      style={{
        flexDirection: 'row',
        alignItems: 'center',
        gap: 12,
        backgroundColor: CARD,
        borderRadius: 14,
        paddingHorizontal: 16,
        paddingVertical: 14,
      }}
    >
      <Ionicons name={icon} size={20} color="#6C47FF" />
      <Text style={{ flex: 1, color: '#FFFFFF', fontSize: 14, fontFamily: 'Inter_400Regular' }}>{label}</Text>
      <Ionicons name="open-outline" size={16} color="#334155" />
    </TouchableOpacity>
  );
}

export default function AboutScreen() {
  return (
    <SafeAreaView style={{ flex: 1, backgroundColor: BG }} edges={['top']}>
      {/* Header */}
      <View style={{ flexDirection: 'row', alignItems: 'center', gap: 12, paddingHorizontal: 16, paddingVertical: 14 }}>
        <TouchableOpacity onPress={() => router.back()} hitSlop={{ top: 8, bottom: 8, left: 8, right: 8 }}>
          <Ionicons name="arrow-back" size={22} color="#FFFFFF" />
        </TouchableOpacity>
        <Text style={{ color: '#FFFFFF', fontSize: 18, fontFamily: 'Inter_700Bold' }}>Hakkında</Text>
      </View>

      <View style={{ flex: 1, paddingHorizontal: 20, alignItems: 'center', gap: 32, paddingTop: 40 }}>
        {/* Logo + versiyon */}
        <View style={{ alignItems: 'center', gap: 12 }}>
          <View style={{ shadowColor: '#FFFFFF', shadowOffset: { width: 0, height: 0 }, shadowOpacity: 0.25, shadowRadius: 20 }}>
            <Image
              source={require('../../assets/images/logo.png')}
              style={{ width: 160, height: 64 }}
              resizeMode="contain"
            />
          </View>
          <Text style={{ color: '#64748B', fontSize: 13, fontFamily: 'Inter_400Regular' }}>Versiyon 1.0.0</Text>
          <Text style={{ color: '#94A3B8', fontSize: 14, fontFamily: 'Inter_400Regular', textAlign: 'center', lineHeight: 22 }}>
            Prial, Türkiye'nin önde gelen e-ticaret platformlarındaki ürünleri takip eden, fiyat düşünce sizi bilgilendiren fiyat talep platformudur.
          </Text>
        </View>

        {/* Linkler */}
        <View style={{ width: '100%', gap: 10 }}>
          <LinkRow icon="globe-outline" label="prial.app" url="https://prial.app" />
          <LinkRow icon="mail-outline" label="destek@prial.app" url="mailto:destek@prial.app" />
        </View>

        <Text style={{ color: '#334155', fontSize: 12, fontFamily: 'Inter_400Regular' }}>
          © 2025 Prial. Tüm hakları saklıdır.
        </Text>
      </View>
    </SafeAreaView>
  );
}
