import { formatPrice } from "@/lib/formatPrice";

interface FAQSchemaProps {
  title: string;
  stores: {
    store: string;
    current_price: number | null;
    in_stock: boolean;
  }[];
  predicted_direction: "UP" | "DOWN" | "STABLE" | null;
}

interface FAQItem {
  question: string;
  answer: string;
}

function buildFAQs(props: FAQSchemaProps): FAQItem[] {
  const { title, stores, predicted_direction } = props;
  const activeStores = stores.filter((s) => s.current_price && s.in_stock);
  const sortedStores = [...activeStores].sort(
    (a, b) => (a.current_price ?? Infinity) - (b.current_price ?? Infinity)
  );
  const cheapest = sortedStores[0];
  const faqs: FAQItem[] = [];

  if (cheapest) {
    faqs.push({
      question: `${title} en ucuz nerede satılıyor?`,
      answer: `${title} en ucuz ${formatPrice(cheapest.current_price)} fiyatla ${cheapest.store} mağazasında satılmaktadır.`,
    });
  }

  if (predicted_direction) {
    const directionText =
      predicted_direction === "DOWN"
        ? "düşmesi bekleniyor. Bekleyerek daha uygun fiyata alabilirsiniz."
        : predicted_direction === "UP"
          ? "artması bekleniyor. Şu anki fiyat uygun olabilir."
          : "stabil kalması bekleniyor.";
    faqs.push({
      question: `${title} fiyatı düşer mi?`,
      answer: `Yapay zeka analizimize göre ${title} fiyatının yakın zamanda ${directionText}`,
    });
  }

  if (activeStores.length > 0) {
    faqs.push({
      question: `${title} kaç mağazada satılıyor?`,
      answer: `${title} şu anda ${activeStores.length} farklı mağazada satılmaktadır. Prial ile tüm mağazaların fiyatlarını karşılaştırabilirsiniz.`,
    });
  }

  return faqs;
}

export function FAQSchema(props: FAQSchemaProps) {
  const faqs = buildFAQs(props);
  if (faqs.length === 0) return null;

  const schema = {
    "@context": "https://schema.org",
    "@type": "FAQPage",
    mainEntity: faqs.map((faq) => ({
      "@type": "Question",
      name: faq.question,
      acceptedAnswer: {
        "@type": "Answer",
        text: faq.answer,
      },
    })),
  };

  return (
    <>
      <script
        type="application/ld+json"
        dangerouslySetInnerHTML={{ __html: JSON.stringify(schema) }}
      />
      {/* Visible FAQ section (Google requires visible content for FAQ rich results) */}
      <section className="mt-10">
        <h2 className="text-xl font-bold text-gray-900 mb-4">
          Sık Sorulan Sorular
        </h2>
        <div className="space-y-4">
          {faqs.map((faq, i) => (
            <details
              key={i}
              className="group border border-gray-200 rounded-lg"
            >
              <summary className="flex items-center justify-between cursor-pointer px-5 py-4 text-sm font-medium text-gray-900 hover:bg-gray-50 rounded-lg">
                {faq.question}
                <svg
                  className="w-4 h-4 text-gray-400 group-open:rotate-180 transition-transform"
                  fill="none"
                  viewBox="0 0 24 24"
                  stroke="currentColor"
                >
                  <path
                    strokeLinecap="round"
                    strokeLinejoin="round"
                    strokeWidth={2}
                    d="M19 9l-7 7-7-7"
                  />
                </svg>
              </summary>
              <p className="px-5 pb-4 text-sm text-gray-600 leading-relaxed">
                {faq.answer}
              </p>
            </details>
          ))}
        </div>
      </section>
    </>
  );
}
