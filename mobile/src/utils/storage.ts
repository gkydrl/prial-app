import { Platform } from 'react-native';

const KEYS = {
  ACCESS_TOKEN: 'prial_access_token',
  REFRESH_TOKEN: 'prial_refresh_token',
  ONBOARDING_DONE: 'prial_onboarding_done',
} as const;

// Web'de SecureStore çalışmaz — localStorage ile fallback
const store =
  Platform.OS === 'web'
    ? {
        getItemAsync: (key: string): Promise<string | null> =>
          Promise.resolve(localStorage.getItem(key)),
        setItemAsync: (key: string, value: string): Promise<void> => {
          localStorage.setItem(key, value);
          return Promise.resolve();
        },
        deleteItemAsync: (key: string): Promise<void> => {
          localStorage.removeItem(key);
          return Promise.resolve();
        },
      }
    : require('expo-secure-store');

export async function getAccessToken(): Promise<string | null> {
  return store.getItemAsync(KEYS.ACCESS_TOKEN);
}

export async function getRefreshToken(): Promise<string | null> {
  return store.getItemAsync(KEYS.REFRESH_TOKEN);
}

export async function setTokens(access: string, refresh: string): Promise<void> {
  await Promise.all([
    store.setItemAsync(KEYS.ACCESS_TOKEN, access),
    store.setItemAsync(KEYS.REFRESH_TOKEN, refresh),
  ]);
}

export async function clearTokens(): Promise<void> {
  await Promise.all([
    store.deleteItemAsync(KEYS.ACCESS_TOKEN),
    store.deleteItemAsync(KEYS.REFRESH_TOKEN),
  ]);
}

export async function getOnboardingDone(): Promise<boolean> {
  const val = await store.getItemAsync(KEYS.ONBOARDING_DONE);
  return val === 'true';
}

export async function setOnboardingDone(): Promise<void> {
  await store.setItemAsync(KEYS.ONBOARDING_DONE, 'true');
}
