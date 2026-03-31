import type { ProductResponse, ProductStoreResponse } from "@/lib/api";
import { formatPrice } from "@/lib/formatPrice";
import { storeLabel } from "@/lib/stores";
import { SignalBadge } from "@/components/ui/SignalBadge";

interface Props {
  product: ProductResponse;
  bestStore: ProductStoreResponse | null;
}

const CARD_CONFIG = {
  AL: {
    bg: "bg-success/10",
    border: "border-success/30",
    badgeBg: "bg-success",
  },
  BEKLE: {
    bg: "bg-bekle/10",
    border: "border-bekle/30",
    badgeBg: "bg-bekle",
  },
  GUCLU_BEKLE: {
    bg: "bg-danger/10",
    border: "border-danger/30",
    badgeBg: "bg-danger",
  },
} as const;

export function PredictionCard({ product, bestStore }: Props) {
  const rec = product.recommendation;
  const config = rec ? CARD_CONFIG[rec] : null;

  // No prediction available
  if (!config) {
    return (
      <div className="rounded-2xl border border-gray-200 bg-gray-50 p-6">
        <div className="flex items-center gap-3">
          <div className="w-10 h-10 rounded-full bg-gray-200 flex items-center justify-center">
            <svg className="w-5 h-5 text-gray-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9.663 17h4.673M12 3v1m6.364 1.636l-.707.707M21 12h-1M4 12H3m3.343-5.657l-.707-.707m2.828 9.9a5 5 0 117.072 0l-.548.547A3.374 3.374 0 0014 18.469V19a2 2 0 11-4 0v-.531c0-.895-.356-1.754-.988-2.386l-.548-.547z" />
            </svg>
          </div>
          <div>
            <p className="font-semibold text-gray-700">AI Analizi Bekleniyor</p>
            <p className="text-sm text-gray-500">Bu ürün için tahmin henüz oluşturulmadı.</p>
          </div>
        </div>
      </div>
    );
  }

  const isAl = rec === "AL";
  const isBekle = rec === "BEKLE" || rec === "GUCLU_BEKLE";

  return (
    <div className={`rounded-2xl border-2 ${config.border} ${config.bg} p-6`}>
      {/* Badge + Confidence */}
      <div className="flex items-center justify-between mb-4">
        <div className="flex items-center gap-3">
          <SignalBadge recommendation={rec!} size="lg" />
          {product.prediction_confidence != null && (
            <span className="text-xs text-gray-500">
              %{Math.round(product.prediction_confidence * 100)} güven
            </span>
          )}
        </div>
        <span className={`text-xs font-medium px-2 py-1 rounded-full ${config.badgeBg} text-white`}>
          AI Tavsiyesi
        </span>
      </div>

      {/* Summary */}
      {product.reasoning_text && (
        <p className="text-sm text-gray-700 leading-relaxed mb-4">
          {product.reasoning_text}
        </p>
      )}

      {/* Pros & Cons */}
      {(product.reasoning_pros || product.reasoning_cons) && (
        <div className="grid grid-cols-1 sm:grid-cols-2 gap-3 mb-4">
          {/* Pros */}
          {product.reasoning_pros && product.reasoning_pros.length > 0 && (
            <div className="space-y-1.5">
              {product.reasoning_pros.map((pro, i) => (
                <div key={i} className="flex items-start gap-2 text-sm">
                  <svg className="w-4 h-4 text-success flex-shrink-0 mt-0.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
                  </svg>
                  <span className="text-gray-700">{pro}</span>
                </div>
              ))}
            </div>
          )}
          {/* Cons */}
          {product.reasoning_cons && product.reasoning_cons.length > 0 && (
            <div className="space-y-1.5">
              {product.reasoning_cons.map((con, i) => (
                <div key={i} className="flex items-start gap-2 text-sm">
                  <svg className="w-4 h-4 text-danger flex-shrink-0 mt-0.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
                  </svg>
                  <span className="text-gray-700">{con}</span>
                </div>
              ))}
            </div>
          )}
        </div>
      )}

      {/* AL → Best store link */}
      {isAl && bestStore && (
        <div className="mb-4 p-3 bg-white rounded-xl border border-gray-100">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-xs text-gray-500">En ucuz fiyat</p>
              <p className="text-xl font-bold text-gray-900">
                {formatPrice(bestStore.current_price)}
              </p>
              <p className="text-xs text-gray-500">
                {storeLabel(bestStore.store)}
              </p>
            </div>
            <a
              href={bestStore.url}
              target="_blank"
              rel="noopener noreferrer"
              className="inline-flex items-center gap-2 bg-success text-white font-semibold py-2.5 px-5 rounded-xl hover:bg-success/90 transition-colors text-sm"
            >
              Mağazaya Git
              <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M10 6H6a2 2 0 00-2 2v10a2 2 0 002 2h10a2 2 0 002-2v-4M14 4h6m0 0v6m0-6L10 14" />
              </svg>
            </a>
          </div>
        </div>
      )}

      {/* BEKLE → Target price + Kampanya Talep Et */}
      {isBekle && (
        <div className="mb-4 p-3 bg-white rounded-xl border border-gray-100">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-xs text-gray-500">Hedef fiyat</p>
              <p className="text-xl font-bold text-gray-900">
                {product.l1y_lowest_price
                  ? formatPrice(product.l1y_lowest_price)
                  : product.lowest_price_ever
                    ? formatPrice(product.lowest_price_ever)
                    : "—"}
              </p>
              <p className="text-xs text-gray-500">Son 1 yılın en düşüğü</p>
            </div>
            <a
              href={`prial://product/${product.id}?action=alarm`}
              className={`inline-flex items-center gap-2 ${config.badgeBg} text-white font-semibold py-2.5 px-5 rounded-xl hover:opacity-90 transition-opacity text-sm`}
            >
              Kampanya Talep Et
              <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M7 7h.01M7 3h5c.512 0 1.024.195 1.414.586l7 7a2 2 0 010 2.828l-7 7a2 2 0 01-2.828 0l-7-7A2 2 0 013 12V7a4 4 0 014-4z" />
              </svg>
            </a>
          </div>
        </div>
      )}

      {/* Social proof */}
      {product.alarm_count > 0 && (
        <p className="text-xs text-gray-500 text-center">
          {product.alarm_count} kişi takip ediyor
        </p>
      )}
    </div>
  );
}
