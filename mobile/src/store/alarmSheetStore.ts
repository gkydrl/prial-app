import { create } from 'zustand';

interface AlarmSheetParams {
  productId: string;
  storeUrl: string | null;
  currentPrice: number | null;
  existingAlarmId?: string;       // set → update mode
  existingTargetPrice?: number;   // slider başlangıç değeri (update mode)
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
  existingAlarmId: undefined,
  existingTargetPrice: undefined,
  open: (params) => set({ visible: true, ...params }),
  close: () => set({ visible: false, existingAlarmId: undefined, existingTargetPrice: undefined }),
}));

export const openAlarmSheet = (params: AlarmSheetParams) => {
  useAlarmSheetStore.getState().open(params);
};
