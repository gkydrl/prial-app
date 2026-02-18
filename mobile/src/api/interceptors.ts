import type { AxiosInstance, InternalAxiosRequestConfig } from 'axios';
import { getAccessToken, getRefreshToken, setTokens, clearTokens } from '@/utils/storage';
import { ENDPOINTS } from '@/constants/api';

interface RetryConfig extends InternalAxiosRequestConfig {
  _retry?: boolean;
}

interface QueueItem {
  resolve: (token: string) => void;
  reject: (error: unknown) => void;
}

let isRefreshing = false;
let failedQueue: QueueItem[] = [];

function processQueue(error: unknown, token: string | null) {
  failedQueue.forEach((item) => {
    if (error) {
      item.reject(error);
    } else {
      item.resolve(token!);
    }
  });
  failedQueue = [];
}

export function setupInterceptors(instance: AxiosInstance) {
  // Request: Authorization header ekle
  instance.interceptors.request.use(async (config) => {
    const token = await getAccessToken();
    if (token) {
      config.headers.Authorization = `Bearer ${token}`;
    }
    return config;
  });

  // Response: 401 → token refresh
  instance.interceptors.response.use(
    (response) => response,
    async (error) => {
      const originalRequest = error.config as RetryConfig;

      if (error.response?.status !== 401 || originalRequest._retry) {
        // Refresh token da geçersiz → çıkış yap
        if (originalRequest._retry) {
          const { useAuthStore } = await import('@/store/authStore');
          useAuthStore.getState().logout();
        }
        return Promise.reject(error);
      }

      if (isRefreshing) {
        // Başka bir refresh devam ediyor, kuyruğa al
        return new Promise<string>((resolve, reject) => {
          failedQueue.push({ resolve, reject });
        }).then((token) => {
          originalRequest.headers.Authorization = `Bearer ${token}`;
          return instance(originalRequest);
        });
      }

      originalRequest._retry = true;
      isRefreshing = true;

      try {
        const refreshToken = await getRefreshToken();
        if (!refreshToken) throw new Error('Refresh token bulunamadı');

        // Backend query param olarak bekliyor
        const { data } = await instance.post(
          `${ENDPOINTS.REFRESH}?refresh_token=${encodeURIComponent(refreshToken)}`
        );

        await setTokens(data.access_token, data.refresh_token);

        const { useAuthStore } = await import('@/store/authStore');
        useAuthStore.getState().setTokens(data.access_token, data.refresh_token);

        processQueue(null, data.access_token);
        originalRequest.headers.Authorization = `Bearer ${data.access_token}`;
        return instance(originalRequest);
      } catch (refreshError) {
        processQueue(refreshError, null);
        await clearTokens();
        const { useAuthStore } = await import('@/store/authStore');
        useAuthStore.getState().logout();
        return Promise.reject(refreshError);
      } finally {
        isRefreshing = false;
      }
    }
  );
}
