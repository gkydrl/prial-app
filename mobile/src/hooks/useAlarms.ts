import { useEffect } from 'react';
import { useAlarmStore } from '@/store/alarmStore';
import type { AlarmStatus } from '@/types/api';

export function useAlarms(status?: AlarmStatus) {
  const alarms = useAlarmStore((s) => s.alarms);
  const isLoading = useAlarmStore((s) => s.isLoading);
  const error = useAlarmStore((s) => s.error);
  const fetchAlarms = useAlarmStore((s) => s.fetchAlarms);
  const deleteAlarm = useAlarmStore((s) => s.deleteAlarm);
  const updateAlarm = useAlarmStore((s) => s.updateAlarm);

  useEffect(() => {
    fetchAlarms(status);
  }, [status]);

  const refresh = () => fetchAlarms(status);

  return { alarms, isLoading, error, deleteAlarm, updateAlarm, refresh };
}
