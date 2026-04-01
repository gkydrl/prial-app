import { useState } from 'react';
import { Platform } from 'react-native';
import * as Google from 'expo-auth-session/providers/google';
import * as AppleAuthentication from 'expo-apple-authentication';
import * as WebBrowser from 'expo-web-browser';
import { useAuthStore } from '@/store/authStore';
import Constants from 'expo-constants';

WebBrowser.maybeCompleteAuthSession();

const GOOGLE_WEB_CLIENT_ID = Constants.expoConfig?.extra?.googleWebClientId ?? '';
const GOOGLE_IOS_CLIENT_ID = Constants.expoConfig?.extra?.googleIosClientId ?? '';
const GOOGLE_ANDROID_CLIENT_ID = Constants.expoConfig?.extra?.googleAndroidClientId ?? '';

export function useSocialAuth() {
  const socialLogin = useAuthStore((s) => s.socialLogin);
  const [loading, setLoading] = useState<'google' | 'apple' | null>(null);

  const [, googleResponse, googlePromptAsync] = Google.useIdTokenAuthRequest({
    clientId: GOOGLE_WEB_CLIENT_ID,
    iosClientId: GOOGLE_IOS_CLIENT_ID,
    androidClientId: GOOGLE_ANDROID_CLIENT_ID,
  });

  const handleGoogleLogin = async (): Promise<{ needs_consent: boolean } | null> => {
    setLoading('google');
    try {
      const result = await googlePromptAsync();
      if (result.type !== 'success') return null;

      const idToken = result.params.id_token;
      if (!idToken) return null;

      const loginResult = await socialLogin('google', idToken);
      return { needs_consent: loginResult.needs_consent };
    } finally {
      setLoading(null);
    }
  };

  const handleAppleLogin = async (): Promise<{ needs_consent: boolean } | null> => {
    if (Platform.OS !== 'ios') return null;

    setLoading('apple');
    try {
      const credential = await AppleAuthentication.signInAsync({
        requestedScopes: [
          AppleAuthentication.AppleAuthenticationScope.FULL_NAME,
          AppleAuthentication.AppleAuthenticationScope.EMAIL,
        ],
      });

      if (!credential.identityToken) return null;

      const fullName = [credential.fullName?.givenName, credential.fullName?.familyName]
        .filter(Boolean)
        .join(' ') || undefined;

      const loginResult = await socialLogin('apple', credential.identityToken, fullName);
      return { needs_consent: loginResult.needs_consent };
    } catch (e: any) {
      if (e.code === 'ERR_REQUEST_CANCELED') return null;
      throw e;
    } finally {
      setLoading(null);
    }
  };

  return {
    handleGoogleLogin,
    handleAppleLogin,
    loading,
    isAppleAvailable: Platform.OS === 'ios',
  };
}
