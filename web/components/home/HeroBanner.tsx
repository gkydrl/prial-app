"use client";

import { useEffect, useRef, useState } from "react";
import { motion, useInView, animate } from "framer-motion";
import { SignalBadge } from "@/components/ui/SignalBadge";

import type { Variants } from "framer-motion";

const container: Variants = {
  hidden: {},
  show: { transition: { staggerChildren: 0.15 } },
};

const fadeUp: Variants = {
  hidden: { opacity: 0, y: 30 },
  show: { opacity: 1, y: 0, transition: { duration: 0.5, ease: "easeOut" as const } },
};

function useCountUp(target: number, duration = 1.5) {
  const [value, setValue] = useState(0);
  const ref = useRef<HTMLSpanElement>(null);
  const inView = useInView(ref, { once: true });

  useEffect(() => {
    if (!inView) return;
    const controls = animate(0, target, {
      duration,
      ease: "easeOut",
      onUpdate(v) {
        setValue(Math.round(v));
      },
    });
    return () => controls.stop();
  }, [inView, target, duration]);

  return { ref, value };
}

export function HeroBanner() {
  const stat1 = useCountUp(10000);
  const stat2 = useCountUp(50);

  return (
    <section className="bg-gradient-to-br from-brand-dark via-brand to-brand-light text-white">
      <motion.div
        className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-16 md:py-24 text-center"
        variants={container}
        initial="hidden"
        animate="show"
      >
        <motion.h1
          variants={fadeUp}
          className="text-4xl md:text-5xl lg:text-6xl font-bold leading-tight"
        >
          Al, Bekle ya da Talep Et
          <br />
          <span className="inline-flex items-baseline gap-3">
            <img
              src="/logo-white.png"
              alt="Prial"
              className="inline h-10 md:h-14 lg:h-16 w-auto align-baseline relative top-1.5 md:top-2"
            />
            <span className="text-white/90">Sana Söylesin</span>
          </span>
        </motion.h1>

        <motion.p
          variants={fadeUp}
          className="mt-4 text-lg md:text-xl text-white/70 max-w-2xl mx-auto"
        >
          Prial ürünü analiz eder ve sana üç net sinyal verir:
          şimdi al, bekle ya da dikkat et. Doğru fiyata gelince
          kampanya talep et, satıcılar sana gelsin.
        </motion.p>

        {/* Signal pills */}
        <motion.div
          variants={fadeUp}
          className="mt-6 flex justify-center gap-3 flex-wrap"
        >
          <span className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-full border border-white/20 bg-white/10 text-sm text-white/90">
            <span className="w-2 h-2 rounded-full bg-success flex-shrink-0" />
            Şimdi Al
          </span>
          <span className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-full border border-white/20 bg-white/10 text-sm text-white/90">
            <span className="w-2 h-2 rounded-full bg-bekle flex-shrink-0" />
            Bekle
          </span>
          <span className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-full border border-white/20 bg-white/10 text-sm text-white/90">
            <span className="w-2 h-2 rounded-full bg-danger flex-shrink-0" />
            Dikkat Et
          </span>
        </motion.div>

        {/* Stats */}
        <motion.div
          variants={fadeUp}
          className="mt-10 flex justify-center gap-8 md:gap-16"
        >
          <div>
            <p className="text-2xl md:text-3xl font-bold text-white">
              <span ref={stat1.ref}>
                {stat1.value.toLocaleString("tr-TR")}
              </span>
              +
            </p>
            <p className="text-sm text-white/60">Takip Edilen Ürün</p>
          </div>
          <div>
            <p className="text-2xl md:text-3xl font-bold text-white">
              Her Gün
            </p>
            <p className="text-sm text-white/60">Güncellenen Fiyatlar</p>
          </div>
          <div>
            <p className="text-2xl md:text-3xl font-bold text-white">
              <span ref={stat2.ref}>{stat2.value}</span>+
            </p>
            <p className="text-sm text-white/60">Desteklenen Mağaza</p>
          </div>
        </motion.div>

        {/* App Store Button */}
        <motion.div
          variants={fadeUp}
          className="mt-10 flex flex-col sm:flex-row items-center justify-center gap-3"
        >
          <a
            href="https://apps.apple.com/tr/app/prial/id6760142538"
            target="_blank"
            rel="noopener noreferrer"
            className="inline-flex items-center gap-2 bg-white text-gray-900 px-6 py-3 rounded-xl font-semibold text-sm hover:bg-gray-100 transition-colors shadow-lg"
          >
            <svg
              className="w-6 h-6"
              viewBox="0 0 24 24"
              fill="currentColor"
            >
              <path d="M18.71 19.5c-.83 1.24-1.71 2.45-3.05 2.47-1.34.03-1.77-.79-3.29-.79-1.53 0-2 .77-3.27.82-1.31.05-2.3-1.32-3.14-2.53C4.25 17 2.94 12.45 4.7 9.39c.87-1.52 2.43-2.48 4.12-2.51 1.28-.02 2.5.87 3.29.87.78 0 2.26-1.07 3.8-.91.65.03 2.47.26 3.64 1.98-.09.06-2.17 1.28-2.15 3.81.03 3.02 2.65 4.03 2.68 4.04-.03.07-.42 1.44-1.38 2.83M13 3.5c.73-.83 1.94-1.46 2.94-1.5.13 1.17-.34 2.35-1.04 3.19-.69.85-1.83 1.51-2.95 1.42-.15-1.15.41-2.35 1.05-3.11z" />
            </svg>
            App Store
          </a>
        </motion.div>
      </motion.div>
    </section>
  );
}
