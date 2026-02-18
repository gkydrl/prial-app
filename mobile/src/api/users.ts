import client from './client';
import { ENDPOINTS } from '@/constants/api';
import type { UserResponse, UserUpdatePreferences } from '@/types/api';

export const usersApi = {
  getProfile: () => client.get<UserResponse>(ENDPOINTS.USER_ME),

  updatePreferences: (payload: UserUpdatePreferences) =>
    client.patch<UserResponse>(ENDPOINTS.USER_ME, payload),

  updateFirebaseToken: (firebase_token: string) =>
    client.post<UserResponse>(ENDPOINTS.USER_FIREBASE_TOKEN, { firebase_token }),
};
