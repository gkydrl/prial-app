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
import { HeroBanner } from "@/components/home/HeroBanner";
import { HowItWorks } from "@/components/home/HowItWorks";
import { SignalBadge } from "@/components/ui/SignalBadge";
import {
  Smartphone, Laptop, Monitor, Tablet, Headphones, Watch,
  Tv, Gamepad2, Camera, Speaker, Home, Refrigerator,
  ShieldCheck, HardDrive, Wifi, Dumbbell, Bike, Plug,
  Scissors, Package,
} from "lucide-react";

export const metadata: Metadata = {
  title: "Prial - Akıllı Alışveriş Asistanı | Fiyat Karşılaştırma & Takip",
  description:
    "Binlerce üründe fiyat karşılaştırması, fiyat geçmişi ve düşüş bildirimi. Trendyol, Hepsiburada, Amazon ve daha fazlasında en ucuz fiyatı bul.",
  openGraph: {
    title: "Prial - Akıllı Alışveriş Asistanı",
    description:
      "Binlerce üründe fiyat karşılaştırması, fiyat geçmişi ve düşüş bildirimi.",
    url: "https://www.prial.io",
    siteName: "Prial",
    type: "website",
    locale: "tr_TR",
  },
  twitter: {
    card: "summary_large_image",
    title: "Prial - Akıllı Alışveriş Asistanı",
    description:
      "Binlerce üründe fiyat karşılaştırması, fiyat geçmişi ve düşüş bildirimi.",
  },
  alternates: {
    canonical: "https://www.prial.io",
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
      <HeroBanner />

      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        {/* How It Works */}
        <HowItWorks />

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

        {/* AI: Şimdi Al */}
        {aiPicks.length > 0 && (
          <section className="py-10">
            <div className="flex items-center justify-between mb-6">
              <div className="flex items-center gap-3">
                <SignalBadge recommendation="IYI_FIYAT" size="md" showLabel={false} />
                <Link href="/kampanyalar?tab=iyi-fiyat" className="text-2xl font-bold text-gray-900 hover:text-brand transition-colors group/link flex items-center gap-1.5">
                  Şimdi Almaya Değer
                  <svg className="w-5 h-5 text-gray-300 group-hover/link:text-brand group-hover/link:translate-x-0.5 transition-all" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2.5}>
                    <path strokeLinecap="round" strokeLinejoin="round" d="M9 5l7 7-7 7" />
                  </svg>
                </Link>
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
                <Link href="/kampanyalar?tab=fiyat-dusecek" className="text-2xl font-bold text-gray-900 hover:text-brand transition-colors group/link flex items-center gap-1.5">
                  Fiyatı Düşecek Ürünler
                  <svg className="w-5 h-5 text-gray-300 group-hover/link:text-brand group-hover/link:translate-x-0.5 transition-all" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2.5}>
                    <path strokeLinecap="round" strokeLinejoin="round" d="M9 5l7 7-7 7" />
                  </svg>
                </Link>
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
