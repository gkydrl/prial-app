"use client";

import { useState } from "react";

export function StickyMobileCTA() {
  const [dismissed, setDismissed] = useState(false);

  if (dismissed) return null;

  return (
    <div className="fixed bottom-0 left-0 right-0 z-50 md:hidden bg-white border-t border-gray-200 shadow-[0_-4px_12px_rgba(0,0,0,0.1)] px-4 py-3">
      <div className="flex items-center gap-3">
        {/* App icon placeholder */}
        <div className="w-10 h-10 rounded-xl bg-brand flex items-center justify-center flex-shrink-0">
          <span className="text-white font-bold text-lg">P</span>
        </div>

        <div className="flex-1 min-w-0">
          <p className="text-sm font-semibold text-gray-900 truncate">
            Prial Uygulaması
          </p>
          <p className="text-xs text-gray-500">
            Fiyat düşünce bildirim al
          </p>
        </div>

        <a
          href="https://apps.apple.com/app/prial"
          target="_blank"
          rel="noopener noreferrer"
          className="flex-shrink-0 bg-brand text-white text-sm font-semibold px-4 py-2 rounded-lg hover:bg-brand-dark transition-colors"
        >
          İndir
        </a>

        <button
          onClick={() => setDismissed(true)}
          className="flex-shrink-0 p-1 text-gray-400 hover:text-gray-600"
          aria-label="Kapat"
        >
          <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
          </svg>
        </button>
      </div>
    </div>
  );
}
