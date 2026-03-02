import { create } from 'zustand';

export type StoredNotification = {
  id: string;
  title: string | null;
  body: string | null;
  data: Record<string, unknown>;
  receivedAt: string; // ISO string
  read: boolean;
};

type NotificationStore = {
  notifications: StoredNotification[];
  unreadCount: number;
  addNotification: (n: Omit<StoredNotification, 'read'>) => void;
  markAllRead: () => void;
  clear: () => void;
};

export const useNotificationStore = create<NotificationStore>((set) => ({
  notifications: [],
  unreadCount: 0,

  addNotification: (n) =>
    set((s) => {
      // Aynı id tekrar eklenmesin
      if (s.notifications.some((x) => x.id === n.id)) return s;
      return {
        notifications: [{ ...n, read: false }, ...s.notifications].slice(0, 50),
        unreadCount: s.unreadCount + 1,
      };
    }),

  markAllRead: () =>
    set((s) => ({
      notifications: s.notifications.map((n) => ({ ...n, read: true })),
      unreadCount: 0,
    })),

  clear: () => set({ notifications: [], unreadCount: 0 }),
}));
