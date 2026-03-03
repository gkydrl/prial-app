import { Modal, View, Text, TouchableOpacity } from 'react-native';
import { useAlertStore } from '@/store/alertStore';

export function AppAlert() {
  const { visible, title, message, buttons, hide } = useAlertStore();

  return (
    <Modal transparent visible={visible} animationType="fade" statusBarTranslucent>
      <View
        style={{
          flex: 1,
          backgroundColor: 'rgba(0,0,0,0.6)',
          justifyContent: 'center',
          alignItems: 'center',
          paddingHorizontal: 32,
        }}
      >
        <View
          style={{
            backgroundColor: '#1E293B',
            borderRadius: 20,
            paddingHorizontal: 24,
            paddingTop: 28,
            paddingBottom: 20,
            width: '100%',
            gap: 10,
          }}
        >
          <Text
            style={{
              color: '#FFFFFF',
              fontSize: 17,
              fontFamily: 'Inter_700Bold',
              textAlign: 'center',
            }}
          >
            {title}
          </Text>

          {message ? (
            <Text
              style={{
                color: '#94A3B8',
                fontSize: 14,
                fontFamily: 'Inter_400Regular',
                textAlign: 'center',
                lineHeight: 20,
              }}
            >
              {message}
            </Text>
          ) : null}

          <View style={{ flexDirection: 'row', gap: 8, marginTop: 10 }}>
            {buttons.map((btn, i) => {
              const isCancel = btn.style === 'cancel';
              const isDestructive = btn.style === 'destructive';
              return (
                <TouchableOpacity
                  key={i}
                  activeOpacity={0.8}
                  onPress={() => {
                    hide();
                    btn.onPress?.();
                  }}
                  style={{
                    flex: 1,
                    paddingVertical: 13,
                    borderRadius: 12,
                    alignItems: 'center',
                    backgroundColor: isDestructive
                      ? '#EF4444'
                      : isCancel
                      ? '#0F172A'
                      : '#6C47FF',
                  }}
                >
                  <Text
                    style={{
                      color: '#FFFFFF',
                      fontSize: 15,
                      fontFamily: isCancel ? 'Inter_400Regular' : 'Inter_600SemiBold',
                    }}
                  >
                    {btn.text}
                  </Text>
                </TouchableOpacity>
              );
            })}
          </View>
        </View>
      </View>
    </Modal>
  );
}
