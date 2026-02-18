const formatter = new Intl.NumberFormat('tr-TR', {
  style: 'currency',
  currency: 'TRY',
  minimumFractionDigits: 2,
  maximumFractionDigits: 2,
});

export function formatTRY(value: number | null | undefined): string {
  if (value == null) return '—';
  return formatter.format(value);
}

export function formatCompact(value: number | null | undefined): string {
  if (value == null) return '—';
  if (value >= 1_000_000) return `₺${(value / 1_000_000).toFixed(1)}M`;
  if (value >= 1_000) return `₺${(value / 1_000).toFixed(1)}B`;
  return formatTRY(value);
}
