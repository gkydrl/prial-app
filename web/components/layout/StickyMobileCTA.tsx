"use client";

import { useState } from "react";
import Image from "next/image";

const APP_STORE_URL = "https://apps.apple.com/tr/app/prial/id6760142538";

export function StickyMobileCTA() {
  const [dismissed, setDismissed] = useState(false);

  if (dismissed) return null;

  return (
    <div className="fixed bottom-0 left-0 right-0 z-50 md:hidden bg-brand-dark border-t border-brand shadow-[0_-4px_12px_rgba(0,0,0,0.2)] px-4 py-3">
      <div className="flex items-center gap-3">
        {/* App icon */}
        <div className="w-10 h-10 rounded-xl overflow-hidden flex-shrink-0">
          <Image src="/app-icon.png" alt="Prial" width={40} height={40} />
        </div>

        <div className="flex-1 min-w-0">
          <p className="text-sm font-semibold text-white truncate">
            Prial
          </p>
          <p className="text-xs text-blue-200">
            Akıllı Alışveriş Asistanı
          </p>
        </div>

        <a
          href={APP_STORE_URL}
          target="_blank"
          rel="noopener noreferrer"
          className="flex-shrink-0 bg-white text-brand text-sm font-semibold px-4 py-2 rounded-lg hover:bg-gray-100 transition-colors"
        >
          İndir
        </a>

        <button
          onClick={() => setDismissed(true)}
          className="flex-shrink-0 p-1 text-blue-300 hover:text-white"
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
