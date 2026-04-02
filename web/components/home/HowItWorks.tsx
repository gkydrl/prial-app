"use client";

import { motion, type Variants } from "framer-motion";
import { SignalBadge } from "@/components/ui/SignalBadge";

const headingVariants: Variants = {
  hidden: { opacity: 0, y: 20 },
  show: { opacity: 1, y: 0, transition: { duration: 0.5, ease: "easeOut" as const } },
};

const cardVariants: Variants = {
  hidden: { opacity: 0, y: 40 },
  show: { opacity: 1, y: 0, transition: { duration: 0.5, ease: "easeOut" as const } },
};

const pillVariants: Variants = {
  hidden: { scale: 0 },
  show: {
    scale: 1,
    transition: { type: "spring" as const, stiffness: 400, damping: 15, delay: 0.2 },
  },
};

const lineVariants: Variants = {
  hidden: { scaleX: 0 },
  show: {
    scaleX: 1,
    transition: { duration: 0.6, ease: "easeOut" as const, delay: 0.3 },
  },
};

const steps = [
  {
    number: 1,
    icon: (
      <svg className="w-7 h-7" fill="none" stroke="currentColor" viewBox="0 0 24 24">
        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M9.663 17h4.673M12 3v1m6.364 1.636l-.707.707M21 12h-1M4 12H3m3.343-5.657l-.707-.707m2.828 9.9a5 5 0 117.072 0l-.548.547A3.374 3.374 0 0014 18.469V19a2 2 0 11-4 0v-.531c0-.895-.356-1.754-.988-2.386l-.548-.547z" />
      </svg>
    ),
    title: "AI Fiyat Analizi" as React.ReactNode,
    description: "Yapay zeka, ürünün fiyat geçmişini, mevsimsel trendleri, yaklaşan kampanyaları ve tüm mağazalardaki fiyatları analiz eder." as React.ReactNode,
    detail: "Birden fazla veri kaynağı ve faktör değerlendirilerek en doğru tahmin üretilir." as React.ReactNode,
  },
  {
    number: 2,
    icon: (
      <svg className="w-7 h-7" fill="none" stroke="currentColor" viewBox="0 0 24 24">
        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z" />
      </svg>
    ),
    title: (<>Net Sinyal Al</>),
    description: (<>
      <span className="block mb-2">Prial analizi tamamlayınca sana üç sinyalden birini verir:</span>
      <span className="block flex flex-col gap-1.5">
        <span className="flex items-start gap-2 text-sm">
          <span className="w-2 h-2 rounded-full bg-success flex-shrink-0 mt-1.5" />
          <span><span className="font-semibold text-gray-700 whitespace-nowrap">İyi Fiyat</span> — Şimdi almanın tam zamanı.</span>
        </span>
        <span className="flex items-start gap-2 text-sm">
          <span className="w-2 h-2 rounded-full bg-bekle flex-shrink-0 mt-1.5" />
          <span><span className="font-semibold text-gray-700 whitespace-nowrap">Fiyat Düşebilir</span> — Biraz bekle.</span>
        </span>
        <span className="flex items-start gap-2 text-sm">
          <span className="w-2 h-2 rounded-full bg-danger flex-shrink-0 mt-1.5" />
          <span><span className="font-semibold text-gray-700 whitespace-nowrap">Fiyat Yükselişte</span> — Dikkatli ol.</span>
        </span>
      </span>
    </>),
    detail: (<>Her sinyal güven skoruyla birlikte gelir. Neden bu tavsiyenin verildiğini Türkçe açıklamayla görürsün.</>),
  },
  {
    number: 3,
    icon: (
      <svg className="w-7 h-7" fill="none" stroke="currentColor" viewBox="0 0 24 24">
        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M7 7h.01M7 3h5c.512 0 1.024.195 1.414.586l7 7a2 2 0 010 2.828l-7 7a2 2 0 01-2.828 0l-7-7A2 2 0 013 12V7a4 4 0 014-4z" />
      </svg>
    ),
    title: "Kampanya Talep Et" as React.ReactNode,
    description: (<><SignalBadge recommendation="FIYAT_DUSEBILIR" size="sm" inline className="inline-flex align-middle" /> veya <SignalBadge recommendation="FIYAT_YUKSELISTE" size="sm" inline className="inline-flex align-middle" /> sinyali aldıysan hedef fiyatını belirle. Aynı ürünü isteyen kullanıcılarla birleş — satıcılar toplu talebi görünce sana özel kampanya gönderir.</>),
    detail: "Topluluk gücüyle satıcılar seni dinlesin. Hedef fiyata ulaşılınca anında haberdar ol." as React.ReactNode,
  },
];

export function HowItWorks() {
  return (
    <section className="py-16">
      <div className="text-center mb-12">
        <motion.h2
          variants={headingVariants}
          initial="hidden"
          whileInView="show"
          viewport={{ once: true }}
          className="text-2xl md:text-3xl font-bold text-gray-900"
        >
          Nasıl Çalışır?
        </motion.h2>
        <motion.p
          variants={headingVariants}
          initial="hidden"
          whileInView="show"
          viewport={{ once: true }}
          className="mt-3 text-gray-500 max-w-xl mx-auto"
        >
          Prial her gün ürünleri analiz eder, sana net sinyal verir
          ve doğru fiyatta kampanya talep etmeni sağlar.
        </motion.p>
      </div>

      <div className="relative grid grid-cols-1 md:grid-cols-3 gap-6">
        {steps.map((step, i) => (
          <div key={step.number} className="relative">
            {/* Connector line between cards (md+ only) */}
            {i < steps.length - 1 && (
              <motion.div
                variants={lineVariants}
                initial="hidden"
                whileInView="show"
                viewport={{ once: true }}
                style={{ originX: 0 }}
                className="hidden md:block absolute top-1/2 -right-3 w-6 h-0.5 bg-brand/20 z-0"
              />
            )}

            <motion.div
              variants={cardVariants}
              initial="hidden"
              whileInView="show"
              viewport={{ once: true }}
              transition={{ delay: i * 0.3 }}
              className="relative flex flex-col p-6 rounded-2xl bg-white border border-gray-100 hover:shadow-md hover:border-brand/20 transition-all h-full"
            >
              <div className="flex items-center gap-3 mb-4">
                <div className="w-12 h-12 rounded-xl bg-brand/10 text-brand flex items-center justify-center flex-shrink-0">
                  {step.icon}
                </div>
                <motion.span
                  variants={pillVariants}
                  initial="hidden"
                  whileInView="show"
                  viewport={{ once: true }}
                  transition={{
                    type: "spring",
                    stiffness: 400,
                    damping: 15,
                    delay: i * 0.3 + 0.3,
                  }}
                  className="text-xs font-bold text-brand bg-brand/5 px-2.5 py-1 rounded-full"
                >
                  ADIM {step.number}
                </motion.span>
              </div>
              <h3 className="text-lg font-semibold text-gray-900 mb-2">
                {step.title}
              </h3>
              <div className="text-sm text-gray-600 leading-relaxed">
                {step.description}
              </div>
              <p className="mt-3 text-xs text-gray-400 leading-relaxed border-t border-gray-50 pt-3">
                {step.detail}
              </p>
            </motion.div>
          </div>
        ))}
      </div>
    </section>
  );
}
