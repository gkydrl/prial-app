import { create } from 'zustand';
import { authApi } from '@/api/auth';
import { setTokens, clearTokens, getAccessToken, getRefreshToken, getOnboardingDone, setOnboardingDone } from '@/utils/storage';
import type { UserResponse } from '@/types/api';

interface AuthState {
  user: UserResponse | null;
  accessToken: string | null;
  refreshToken: string | null;
  isAuthenticated: boolean;
  isHydrated: boolean;
  hasCompletedOnboarding: boolean;

  login: (email: string, password: string) => Promise<void>;
  register: (email: string, password: string, fullName?: string) => Promise<void>;
  logout: () => void;
  setTokens: (access: string, refresh: string) => void;
  updateUser: (partial: Partial<UserResponse>) => void;
  hydrate: () => Promise<void>;
  completeOnboarding: () => Promise<void>;
}

export const useAuthStore = create<AuthState>((set, get) => ({
  user: null,
  accessToken: null,
  refreshToken: null,
  isAuthenticated: false,
  isHydrated: false,
  hasCompletedOnboarding: false,

  login: async (email, password) => {
    const { data } = await authApi.login(email, password);
    await setTokens(data.access_token, data.refresh_token);
    set({ accessToken: data.access_token, refreshToken: data.refresh_token });
    const { data: user } = await authApi.me();
    set({ user, isAuthenticated: true });
  },

  register: async (email, password, fullName) => {
    const { data } = await authApi.register(email, password, fullName);
    await setTokens(data.access_token, data.refresh_token);
    set({ accessToken: data.access_token, refreshToken: data.refresh_token });
    const { data: user } = await authApi.me();
    set({ user, isAuthenticated: true });
  },

  logout: () => {
    clearTokens();
    set({ user: null, accessToken: null, refreshToken: null, isAuthenticated: false });
  },

  setTokens: (access, refresh) => {
    set({ accessToken: access, refreshToken: refresh });
  },

  updateUser: (partial) => {
    const current = get().user;
    if (current) set({ user: { ...current, ...partial } });
  },

  hydrate: async () => {
    try {
      const [access, refresh, onboardingDone] = await Promise.all([
        getAccessToken(),
        getRefreshToken(),
        getOnboardingDone(),
      ]);
      if (!access) {
        set({ isHydrated: true });
        return;
      }
      set({ accessToken: access, refreshToken: refresh, hasCompletedOnboarding: onboardingDone });
      const { data: user } = await authApi.me();
      set({ user, isAuthenticated: true });
    } catch {
      await clearTokens();
      set({ isAuthenticated: false });
    } finally {
      set({ isHydrated: true });
    }
  },

  completeOnboarding: async () => {
    await setOnboardingDone();
    set({ hasCompletedOnboarding: true });
  },
}));
