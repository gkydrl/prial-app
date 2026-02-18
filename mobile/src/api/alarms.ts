import client from './client';
import { ENDPOINTS } from '@/constants/api';
import type { AlarmResponse, AlarmStatus, AlarmUpdatePayload } from '@/types/api';

export const alarmsApi = {
  list: (status?: AlarmStatus) =>
    client.get<AlarmResponse[]>(ENDPOINTS.ALARMS, {
      params: status ? { status } : undefined,
    }),

  update: (id: string, payload: AlarmUpdatePayload) =>
    client.patch<AlarmResponse>(ENDPOINTS.ALARM_DETAIL(id), payload),

  delete: (id: string) =>
    client.delete(ENDPOINTS.ALARM_DETAIL(id)),
};
