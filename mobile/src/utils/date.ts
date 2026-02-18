import dayjs from 'dayjs';
import 'dayjs/locale/tr';
import relativeTime from 'dayjs/plugin/relativeTime';

dayjs.extend(relativeTime);
dayjs.locale('tr');

export function formatRelative(dateStr: string): string {
  return dayjs(dateStr).fromNow();
}

export function formatDate(dateStr: string): string {
  return dayjs(dateStr).format('D MMM YYYY');
}

export function formatChartLabel(dateStr: string): string {
  return dayjs(dateStr).format('DD/MM');
}

export function formatDateTime(dateStr: string): string {
  return dayjs(dateStr).format('D MMM YYYY, HH:mm');
}
