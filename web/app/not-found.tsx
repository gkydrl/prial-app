import type { Metadata } from "next";
import Link from "next/link";

export const metadata: Metadata = {
  title: "Sayfa Bulunamadı",
  robots: { index: false, follow: true },
};

export default function NotFound() {
  return (
    <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-24 text-center">
      <h1 className="text-6xl font-bold text-gray-200">404</h1>
      <h2 className="mt-4 text-xl font-semibold text-gray-900">
        Sayfa Bulunamadı
      </h2>
      <p className="mt-2 text-gray-500">
        Aradığınız sayfa mevcut değil veya taşınmış olabilir.
      </p>
      <Link
        href="/"
        className="inline-block mt-6 bg-brand text-white px-6 py-3 rounded-lg font-medium hover:bg-brand-dark transition-colors"
      >
        Ana Sayfaya Dön
      </Link>
    </div>
  );
}
