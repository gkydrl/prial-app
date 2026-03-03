import { create } from 'zustand';

interface AlarmSheetParams {
  productId: string;
  storeUrl: string | null;
  currentPrice: number | null;
}

interface AlarmSheetState extends AlarmSheetParams {
  visible: boolean;
  open: (params: AlarmSheetParams) => void;
  close: () => void;
}

export const useAlarmSheetStore = create<AlarmSheetState>((set) => ({
  visible: false,
  productId: '',
  storeUrl: null,
  currentPrice: null,
  open: (params) => set({ visible: true, ...params }),
  close: () => set({ visible: false }),
}));

export const openAlarmSheet = (params: AlarmSheetParams) => {
  useAlarmSheetStore.getState().open(params);
};
