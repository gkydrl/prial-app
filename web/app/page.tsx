import type { Metadata } from "next";
import Link from "next/link";
import {
  getCategories,
  getDailyDeals,
  getAIPicks,
  getAIWaitPicks,
  filterDisplayable,
} from "@/lib/api";
import { ProductCard } from "@/components/product/ProductCard";
import { AppDownloadCTA } from "@/components/product/AppDownloadCTA";
import { HowItWorks } from "@/components/home/HowItWorks";
import { SignalBadge } from "@/components/ui/SignalBadge";
import {
  Smartphone, Laptop, Monitor, Tablet, Headphones, Watch,
  Tv, Gamepad2, Camera, Speaker, Home, Refrigerator,
  ShieldCheck, HardDrive, Wifi, Dumbbell, Bike, Plug,
  Scissors, Package,
} from "lucide-react";

export const metadata: Metadata = {
  title: "Prial - Akıllı Alışveriş Asistanın | Fiyat Karşılaştırma & Takip",
  description:
    "Binlerce üründe fiyat karşılaştırması, fiyat geçmişi ve düşüş bildirimi. Trendyol, Hepsiburada, Amazon ve daha fazlasında en ucuz fiyatı bul.",
  openGraph: {
    title: "Prial - Akıllı Alışveriş Asistanın",
    description:
      "Binlerce üründe fiyat karşılaştırması, fiyat geçmişi ve düşüş bildirimi.",
    url: "https://prial.io",
    siteName: "Prial",
    type: "website",
    locale: "tr_TR",
  },
  twitter: {
    card: "summary_large_image",
    title: "Prial - Akıllı Alışveriş Asistanın",
    description:
      "Binlerce üründe fiyat karşılaştırması, fiyat geçmişi ve düşüş bildirimi.",
  },
  alternates: {
    canonical: "https://prial.io",
  },
};

export const revalidate = 1800; // 30 dakika ISR

export default async function HomePage() {
  const [categories, rawDeals, rawAIPicks, rawAIWaitPicks] = await Promise.all([
    getCategories().catch(() => []),
    getDailyDeals().catch(() => []),
    getAIPicks().catch(() => []),
    getAIWaitPicks().catch(() => []),
  ]);

  const deals = filterDisplayable(rawDeals);
  const aiPicks = filterDisplayable(rawAIPicks);
  const aiWaitPicks = filterDisplayable(rawAIWaitPicks);

  return (
    <div>
      {/* Hero */}
      <section className="bg-gradient-to-br from-brand-dark via-brand to-brand-light text-white">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-16 md:py-24 text-center">
          <h1 className="text-4xl md:text-5xl lg:text-6xl font-bold leading-tight">
            Alışverişte Doğru Zamanı Bilen Asistanın
          </h1>
          <p className="mt-4 text-lg md:text-xl text-white/70 max-w-2xl mx-auto">
            Prial, takip ettiğin ürünlerin fiyat geçmişini analiz eder.{" "}
            <SignalBadge recommendation="IYI_FIYAT" size="sm" inline className="inline-flex align-middle mx-0.5" />{" "}
            sinyali gelince al,{" "}
            <SignalBadge recommendation="FIYAT_DUSEBILIR" size="sm" inline className="inline-flex align-middle mx-0.5" />{" "}
            diyorsa takip et — paranı boşa harcama.
          </p>

          {/* Stats */}
          <div className="mt-10 flex justify-center gap-8 md:gap-16">
            <div>
              <p className="text-2xl md:text-3xl font-bold text-white">10.000+</p>
              <p className="text-sm text-white/60">Takip Edilen Ürün</p>
            </div>
            <div>
              <p className="text-2xl md:text-3xl font-bold text-white">Her Gün</p>
              <p className="text-sm text-white/60">Güncellenen Fiyatlar</p>
            </div>
            <div>
              <p className="text-2xl md:text-3xl font-bold text-white">50+</p>
              <p className="text-sm text-white/60">Mağaza Karşılaştırma</p>
            </div>
          </div>

          {/* App Store Buttons */}
          <div className="mt-10 flex flex-col sm:flex-row items-center justify-center gap-3">
            <a
              href="https://apps.apple.com/tr/app/prial/id6760142538"
              target="_blank"
              rel="noopener noreferrer"
              className="inline-flex items-center gap-2 bg-white text-gray-900 px-6 py-3 rounded-xl font-semibold text-sm hover:bg-gray-100 transition-colors shadow-lg"
            >
              <svg className="w-6 h-6" viewBox="0 0 24 24" fill="currentColor">
                <path d="M18.71 19.5c-.83 1.24-1.71 2.45-3.05 2.47-1.34.03-1.77-.79-3.29-.79-1.53 0-2 .77-3.27.82-1.31.05-2.3-1.32-3.14-2.53C4.25 17 2.94 12.45 4.7 9.39c.87-1.52 2.43-2.48 4.12-2.51 1.28-.02 2.5.87 3.29.87.78 0 2.26-1.07 3.8-.91.65.03 2.47.26 3.64 1.98-.09.06-2.17 1.28-2.15 3.81.03 3.02 2.65 4.03 2.68 4.04-.03.07-.42 1.44-1.38 2.83M13 3.5c.73-.83 1.94-1.46 2.94-1.5.13 1.17-.34 2.35-1.04 3.19-.69.85-1.83 1.51-2.95 1.42-.15-1.15.41-2.35 1.05-3.11z" />
              </svg>
              App Store
            </a>
          </div>
        </div>
      </section>

      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        {/* How It Works */}
        <HowItWorks />

        {/* AI: Şimdi Al */}
        {aiPicks.length > 0 && (
          <section className="py-10">
            <div className="flex items-center justify-between mb-6">
              <div className="flex items-center gap-3">
                <SignalBadge recommendation="IYI_FIYAT" size="md" showLabel={false} />
                <h2 className="text-2xl font-bold text-gray-900">
                  Şimdi Almaya Değer
                </h2>
              </div>
              <span className="text-xs font-medium px-2 py-1 rounded-full bg-success text-white">
                AI Tavsiyesi
              </span>
            </div>
            <p className="text-sm text-gray-500 -mt-4 mb-5">
              Yapay zeka analizine göre şu an uygun fiyatta olan ürünler.
            </p>
            <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-4 xl:grid-cols-5 gap-4">
              {aiPicks.slice(0, 10).map((product) => (
                <ProductCard key={product.id} product={product} />
              ))}
            </div>
          </section>
        )}

        {/* AI: Düşecek Ürünler */}
        {aiWaitPicks.length > 0 && (
          <section className="py-10">
            <div className="flex items-center justify-between mb-6">
              <div className="flex items-center gap-3">
                <SignalBadge recommendation="FIYAT_DUSEBILIR" size="md" showLabel={false} />
                <h2 className="text-2xl font-bold text-gray-900">
                  Fiyatı Düşecek Ürünler
                </h2>
              </div>
              <span className="text-xs font-medium px-2 py-1 rounded-full bg-bekle text-white">
                Fiyat Düşebilir
              </span>
            </div>
            <p className="text-sm text-gray-500 -mt-4 mb-5 flex items-center flex-wrap gap-1">
              AI analizine göre yakın zamanda fiyat düşüşü beklenen ürünler.
              <SignalBadge recommendation="FIYAT_DUSEBILIR" size="sm" inline />
              — takipte kal, daha uygun fiyata al.
            </p>
            <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-4 xl:grid-cols-5 gap-4">
              {aiWaitPicks.slice(0, 10).map((product) => (
                <ProductCard key={product.id} product={product} />
              ))}
            </div>
          </section>
        )}

        {/* Kategoriler */}
        {categories.length > 0 && (
          <section className="py-10">
            <h2 className="text-2xl font-bold text-gray-900 mb-6">Kategoriler</h2>
            <div className="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-5 gap-4">
              {categories
                .filter((cat) => (cat.product_count ?? 0) > 0)
                .sort((a, b) => (b.product_count ?? 0) - (a.product_count ?? 0))
                .slice(0, 10)
                .map((cat) => (
                <Link
                  key={cat.id}
                  href={`/${cat.slug}`}
                  className="flex flex-col items-center p-4 bg-white rounded-xl border border-gray-100 hover:border-brand/30 hover:shadow-md active:border-brand active:scale-[0.97] transition-all text-center"
                >
                  <div className="mb-2">
                    <CategoryIcon slug={cat.slug} />
                  </div>
                  <span className="text-sm font-medium text-gray-900">
                    {cat.name}
                  </span>
                  <span className="text-xs text-gray-400 mt-1">
                    {cat.product_count} ürün
                  </span>
                </Link>
              ))}
            </div>
          </section>
        )}

        {/* Günün Fırsatları */}
        {deals.length > 0 && (
          <section className="py-10">
            <div className="flex items-center justify-between mb-6">
              <h2 className="text-2xl font-bold text-gray-900">
                Günün Fırsatları
              </h2>
              <span className="text-sm text-gray-500">
                {deals.length} ürün
              </span>
            </div>
            <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-4 xl:grid-cols-5 gap-4">
              {deals.slice(0, 10).map((product) => (
                <ProductCard key={product.id} product={product} />
              ))}
            </div>
          </section>
        )}

        {/* App Download CTA */}
        <section className="py-10">
          <AppDownloadCTA />
        </section>

        {/* SEO Content */}
        <section className="py-10">
          <div className="flex flex-col md:flex-row md:items-start md:gap-8">
            <h2 className="text-2xl font-bold text-gray-900 mb-3 md:mb-0 md:flex-shrink-0">
              Prial ile Akıllı Alışveriş
            </h2>
            <p className="text-sm text-gray-500 leading-relaxed">
              Prial, yapay zeka destekli alışveriş asistanıdır. Her gün binlerce
              ürünü analiz eder ve{" "}
              <SignalBadge recommendation="IYI_FIYAT" size="sm" inline className="inline-flex align-middle mx-0.5" />{" "}
              veya{" "}
              <SignalBadge recommendation="FIYAT_DUSEBILIR" size="sm" inline className="inline-flex align-middle mx-0.5" />{" "}
              tavsiyesi verir. Fiyat geçmişini
              incele, mağazaları karşılaştır ve doğru zamanda alışveriş yap.
              Trendyol, Hepsiburada, Amazon, n11, MediaMarkt ve daha fazlasında
              en bilinçli alışverişi yap.
            </p>
          </div>
        </section>
      </div>
    </div>
  );
}

function CategoryIcon({ slug, className }: { slug: string; className?: string }) {
  const cls = className ?? "w-7 h-7 text-gray-500";
  const map: Record<string, React.ReactNode> = {
    "akilli-telefon": <Smartphone className={cls} />,
    telefon: <Smartphone className={cls} />,
    laptop: <Laptop className={cls} />,
    tablet: <Tablet className={cls} />,
    bilgisayar: <Monitor className={cls} />,
    kulaklik: <Headphones className={cls} />,
    "kulaklik-ses": <Headphones className={cls} />,
    "akilli-saat": <Watch className={cls} />,
    televizyon: <Tv className={cls} />,
    "oyun-konsolu": <Gamepad2 className={cls} />,
    "oyun-gaming": <Gamepad2 className={cls} />,
    kamera: <Camera className={cls} />,
    "fotograf-makinesi": <Camera className={cls} />,
    monitor: <Monitor className={cls} />,
    "ev-aleti": <Home className={cls} />,
    "beyaz-esya": <Refrigerator className={cls} />,
    "akilli-ev": <Home className={cls} />,
    hoparlor: <Speaker className={cls} />,
    guvenlik: <ShieldCheck className={cls} />,
    "kisisel-bakim": <Scissors className={cls} />,
    depolama: <HardDrive className={cls} />,
    "ag-cihazi": <Wifi className={cls} />,
    "spor-fitness": <Dumbbell className={cls} />,
    "e-mobilite": <Bike className={cls} />,
    aksesuar: <Plug className={cls} />,
  };
  return <>{map[slug] ?? <Package className={cls} />}</>;
}
