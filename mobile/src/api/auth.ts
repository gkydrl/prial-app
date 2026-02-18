import client from './client';
import { ENDPOINTS } from '@/constants/api';
import type { TokenResponse, UserResponse } from '@/types/api';

export const authApi = {
  register: (email: string, password: string, full_name?: string) =>
    client.post<TokenResponse>(ENDPOINTS.REGISTER, { email, password, full_name }),

  login: (email: string, password: string) =>
    client.post<TokenResponse>(ENDPOINTS.LOGIN, { email, password }),

  refresh: (refresh_token: string) =>
    client.post<TokenResponse>(`${ENDPOINTS.REFRESH}?refresh_token=${encodeURIComponent(refresh_token)}`),

  me: () => client.get<UserResponse>(ENDPOINTS.ME),
};
