import { ScrollView, View, Text, TouchableOpacity } from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';
import { router } from 'expo-router';
import { Ionicons } from '@expo/vector-icons';

const BG = '#0A1628';

function Section({ title, children }: { title: string; children: string }) {
  return (
    <View style={{ gap: 8 }}>
      <Text style={{ color: '#FFFFFF', fontSize: 15, fontFamily: 'Inter_700Bold' }}>{title}</Text>
      <Text style={{ color: '#94A3B8', fontSize: 13, fontFamily: 'Inter_400Regular', lineHeight: 21 }}>{children}</Text>
    </View>
  );
}

export default function PrivacyScreen() {
  return (
    <SafeAreaView style={{ flex: 1, backgroundColor: BG }} edges={['top']}>
      {/* Header */}
      <View style={{ flexDirection: 'row', alignItems: 'center', gap: 12, paddingHorizontal: 16, paddingVertical: 14 }}>
        <TouchableOpacity onPress={() => router.back()} hitSlop={{ top: 8, bottom: 8, left: 8, right: 8 }}>
          <Ionicons name="arrow-back" size={22} color="#FFFFFF" />
        </TouchableOpacity>
        <Text style={{ color: '#FFFFFF', fontSize: 18, fontFamily: 'Inter_700Bold' }}>Gizlilik Politikası</Text>
      </View>

      <ScrollView
        showsVerticalScrollIndicator={false}
        contentContainerStyle={{ paddingHorizontal: 20, paddingBottom: 40, gap: 24, paddingTop: 8 }}
      >
        <Text style={{ color: '#64748B', fontSize: 12, fontFamily: 'Inter_400Regular' }}>
          Son güncelleme: Ocak 2025
        </Text>

        <Section title="1. Toplanan Bilgiler">
          Prial, hizmetlerimizi sunabilmek için e-posta adresiniz ve ad-soyadınız gibi temel hesap bilgilerini toplar. Uygulama kullanımı sırasında cihaz bilgileri ve anonim kullanım istatistikleri de toplanabilir.
        </Section>

        <Section title="2. Bilgilerin Kullanımı">
          Topladığımız bilgiler; hesap yönetimi, fiyat alarm bildirimleri, uygulama geliştirme ve güvenlik amacıyla kullanılmaktadır. Kişisel bilgileriniz üçüncü taraflarla satılmaz veya kiralanmaz.
        </Section>

        <Section title="3. Bildirimler">
          Talep oluşturduğunuz ürünlerin fiyatı hedef seviyeye ulaştığında push bildirimi gönderilir. Bildirim tercihlerini Ayarlar ekranından yönetebilirsiniz.
        </Section>

        <Section title="4. Veri Güvenliği">
          Verileriniz endüstri standardı şifreleme yöntemleriyle korunmaktadır. Hesabınıza yetkisiz erişim tespit etmeniz durumunda derhal destek ekibimizle iletişime geçin.
        </Section>

        <Section title="5. Veri Saklama ve Silme">
          Hesabınızı silmek istemeniz durumunda destek@prial.app adresine e-posta göndererek tüm verilerinizin silinmesini talep edebilirsiniz. Verileriniz en geç 30 gün içinde sistemden kaldırılır.
        </Section>

        <Section title="6. İletişim">
          Gizlilik politikamıza ilişkin sorularınız için destek@prial.app adresine ulaşabilirsiniz.
        </Section>
      </ScrollView>
    </SafeAreaView>
  );
}
