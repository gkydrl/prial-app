import client from './client';
import { ENDPOINTS } from '@/constants/api';
import type { TokenResponse, SocialLoginResponse, UserResponse } from '@/types/api';

export const authApi = {
  register: (email: string, password: string, full_name?: string) =>
    client.post<TokenResponse>(ENDPOINTS.REGISTER, { email, password, full_name }),

  login: (email: string, password: string) =>
    client.post<TokenResponse>(ENDPOINTS.LOGIN, { email, password }),

  refresh: (refresh_token: string) =>
    client.post<TokenResponse>(`${ENDPOINTS.REFRESH}?refresh_token=${encodeURIComponent(refresh_token)}`),

  me: () => client.get<UserResponse>(ENDPOINTS.ME),

  verifyEmail: (code: string) =>
    client.post(ENDPOINTS.VERIFY_EMAIL, { code }),

  resendVerification: () =>
    client.post(ENDPOINTS.RESEND_VERIFICATION),

  forgotPassword: (email: string) =>
    client.post(ENDPOINTS.FORGOT_PASSWORD, { email }),

  resetPassword: (token: string, new_password: string) =>
    client.post(ENDPOINTS.RESET_PASSWORD, { token, new_password }),

  deleteAccount: () =>
    client.delete(ENDPOINTS.DELETE_ACCOUNT),

  socialLogin: (provider: 'google' | 'apple', id_token: string, full_name?: string) =>
    client.post<SocialLoginResponse>(ENDPOINTS.SOCIAL_LOGIN, { provider, id_token, full_name }),

  saveConsent: (prefs: {
    push_notifications_enabled: boolean;
    email_notifications_enabled: boolean;
    notify_on_price_drop: boolean;
    notify_on_back_in_stock: boolean;
  }) => client.post(ENDPOINTS.CONSENT, prefs),
};
