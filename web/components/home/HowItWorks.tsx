import { SignalBadge } from "@/components/ui/SignalBadge";

export function HowItWorks() {
  return (
    <section className="py-16">
      <div className="text-center mb-12">
        <h2 className="text-2xl md:text-3xl font-bold text-gray-900">
          Nasıl Çalışır?
        </h2>
        <p className="mt-3 text-gray-500 max-w-xl mx-auto">
          Prial, her gün binlerce ürünü analiz eder ve sana en doğru alışveriş kararını verir.
        </p>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
        <Step
          number={1}
          icon={
            <svg className="w-7 h-7" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M9.663 17h4.673M12 3v1m6.364 1.636l-.707.707M21 12h-1M4 12H3m3.343-5.657l-.707-.707m2.828 9.9a5 5 0 117.072 0l-.548.547A3.374 3.374 0 0014 18.469V19a2 2 0 11-4 0v-.531c0-.895-.356-1.754-.988-2.386l-.548-.547z" />
            </svg>
          }
          title="AI Fiyat Analizi"
          description="Yapay zeka, ürünün fiyat geçmişini, mevsimsel trendleri, yaklaşan kampanyaları ve tüm mağazalardaki fiyatları analiz eder."
          detail="Birden fazla veri kaynağı ve faktör değerlendirilerek en doğru tahmin üretilir."
        />
        <Step
          number={2}
          icon={
            <svg className="w-7 h-7" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z" />
            </svg>
          }
          title={<><SignalBadge recommendation="IYI_FIYAT" size="sm" inline className="inline-flex align-middle" /> veya <SignalBadge recommendation="FIYAT_DUSEBILIR" size="sm" inline className="inline-flex align-middle" /></>}
          description={<>Analiz sonucuna göre net bir tavsiye alırsın: <SignalBadge recommendation="IYI_FIYAT" size="sm" inline className="inline-flex align-middle" /> sinyali — fiyat uygun, şimdi al. <SignalBadge recommendation="FIYAT_DUSEBILIR" size="sm" inline className="inline-flex align-middle" /> sinyali — fiyat düşebilir, takipte kal.</>}
          detail={<>Her tavsiye, güven skoruyla birlikte gelir. Neden <SignalBadge recommendation="IYI_FIYAT" size="sm" inline className="inline-flex align-middle" /> veya <SignalBadge recommendation="FIYAT_DUSEBILIR" size="sm" inline className="inline-flex align-middle" /> dendiğini Türkçe açıklamayla görürsün.</>}
        />
        <Step
          number={3}
          icon={
            <svg className="w-7 h-7" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M7 7h.01M7 3h5c.512 0 1.024.195 1.414.586l7 7a2 2 0 010 2.828l-7 7a2 2 0 01-2.828 0l-7-7A2 2 0 013 12V7a4 4 0 014-4z" />
            </svg>
          }
          title="Kampanya Talep Et"
          description={<><SignalBadge recommendation="FIYAT_DUSEBILIR" size="sm" inline className="inline-flex align-middle" /> sinyali gördüğünde hedef fiyatını belirle. Binlerce kişiyle birlikte mağazalardan kampanya talep et.</>}
          detail="Topluluk gücüyle mağazalar seni dinlesin. Fiyat düşünce anında haberdar ol."
        />
      </div>
    </section>
  );
}

function Step({
  number,
  icon,
  title,
  description,
  detail,
}: {
  number: number;
  icon: React.ReactNode;
  title: React.ReactNode;
  description: React.ReactNode;
  detail: React.ReactNode;
}) {
  return (
    <div className="relative flex flex-col p-6 rounded-2xl bg-white border border-gray-100 hover:shadow-md hover:border-brand/20 transition-all">
      <div className="flex items-center gap-3 mb-4">
        <div className="w-12 h-12 rounded-xl bg-brand/10 text-brand flex items-center justify-center flex-shrink-0">
          {icon}
        </div>
        <span className="text-xs font-bold text-brand bg-brand/5 px-2.5 py-1 rounded-full">
          ADIM {number}
        </span>
      </div>
      <h3 className="text-lg font-semibold text-gray-900 mb-2">{title}</h3>
      <p className="text-sm text-gray-600 leading-relaxed">{description}</p>
      <p className="mt-3 text-xs text-gray-400 leading-relaxed border-t border-gray-50 pt-3">
        {detail}
      </p>
    </div>
  );
}
