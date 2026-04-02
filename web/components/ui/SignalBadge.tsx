/**
 * İyi Fiyat / Fiyat Düşebilir sinyal göstergesi — trafik lambası konsepti.
 * Yeşil daire = İyi Fiyat, turuncu daire = Fiyat Düşebilir, kırmızı daire = Fiyat Yükselişte.
 */

type Recommendation = "IYI_FIYAT" | "FIYAT_DUSEBILIR" | "FIYAT_YUKSELISTE";
type Size = "sm" | "md" | "lg";

const CONFIG = {
  IYI_FIYAT: {
    color: "bg-success",
    glow: "shadow-[0_0_6px_rgba(22,163,74,0.5)]",
    label: "İyi Fiyat",
  },
  FIYAT_DUSEBILIR: {
    color: "bg-bekle",
    glow: "shadow-[0_0_6px_rgba(245,158,11,0.5)]",
    label: "Fiyat Düşebilir",
  },
  FIYAT_YUKSELISTE: {
    color: "bg-danger",
    glow: "shadow-[0_0_6px_rgba(220,38,38,0.5)]",
    label: "Fiyat Yükselişte",
  },
} as const;

const SIZES = {
  sm: { dot: "w-2 h-2", text: "text-xs", gap: "gap-1", px: "px-2 py-0.5" },
  md: { dot: "w-2.5 h-2.5", text: "text-sm font-medium", gap: "gap-1.5", px: "px-2.5 py-1" },
  lg: { dot: "w-3 h-3", text: "text-base font-semibold", gap: "gap-2", px: "px-3 py-1.5" },
} as const;

interface Props {
  recommendation: Recommendation;
  size?: Size;
  /** When true, label inherits surrounding font size instead of using its own. */
  inline?: boolean;
  showLabel?: boolean;
  className?: string;
}

export function SignalBadge({ recommendation, size = "md", inline = false, showLabel = true, className = "" }: Props) {
  const cfg = CONFIG[recommendation as Recommendation];
  if (!cfg) return null;
  const sz = inline ? SIZES.sm : SIZES[size];

  return (
    <span className={`inline-flex items-center ${sz.gap} ${sz.px} rounded-full bg-gray-100 ${className}`}>
      <span className={`${sz.dot} rounded-full ${cfg.color} ${cfg.glow} flex-shrink-0 signal-pulse`} />
      {showLabel && (
        <span className={`${sz.text} text-gray-700 font-semibold`}>
          {cfg.label}
        </span>
      )}
    </span>
  );
}
