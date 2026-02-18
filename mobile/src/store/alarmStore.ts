import { create } from 'zustand';
import { alarmsApi } from '@/api/alarms';
import type { AlarmResponse, AlarmStatus, AlarmUpdatePayload } from '@/types/api';

interface AlarmState {
  alarms: AlarmResponse[];
  isLoading: boolean;
  error: string | null;

  fetchAlarms: (status?: AlarmStatus) => Promise<void>;
  deleteAlarm: (id: string) => Promise<void>;
  updateAlarm: (id: string, payload: AlarmUpdatePayload) => Promise<void>;
}

export const useAlarmStore = create<AlarmState>((set, get) => ({
  alarms: [],
  isLoading: false,
  error: null,

  fetchAlarms: async (status) => {
    set({ isLoading: true, error: null });
    try {
      const { data } = await alarmsApi.list(status);
      set({ alarms: data });
    } catch (e: any) {
      set({ error: e.message ?? 'Alarmlar yüklenemedi' });
    } finally {
      set({ isLoading: false });
    }
  },

  deleteAlarm: async (id) => {
    const prev = get().alarms;
    // Optimistic: hemen listeden çıkar
    set({ alarms: prev.filter((a) => a.id !== id) });
    try {
      await alarmsApi.delete(id);
    } catch (e: any) {
      // Hata → geri al
      set({ alarms: prev, error: e.message ?? 'Alarm silinemedi' });
    }
  },

  updateAlarm: async (id, payload) => {
    const prev = get().alarms;
    // Optimistic: state'i güncelle
    set({
      alarms: prev.map((a) =>
        a.id === id ? { ...a, ...payload } : a
      ),
    });
    try {
      const { data } = await alarmsApi.update(id, payload);
      set({ alarms: prev.map((a) => (a.id === id ? data : a)) });
    } catch (e: any) {
      // Hata → geri al
      set({ alarms: prev, error: e.message ?? 'Alarm güncellenemedi' });
    }
  },
}));
