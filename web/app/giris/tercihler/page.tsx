"use client";

import { useState, useEffect } from "react";
import { useRouter } from "next/navigation";
import { saveConsent, isLoggedIn, fetchMe } from "@/lib/auth";

export default function ConsentPage() {
  const router = useRouter();
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [userName, setUserName] = useState<string | null>(null);

  const [prefs, setPrefs] = useState({
    push_notifications_enabled: false,
    email_notifications_enabled: false,
    notify_on_price_drop: false,
    notify_on_back_in_stock: false,
  });

  useEffect(() => {
    if (!isLoggedIn()) {
      router.replace("/giris");
      return;
    }
    fetchMe()
      .then((user) => setUserName(user.full_name))
      .catch(() => {});
  }, [router]);

  const toggle = (key: keyof typeof prefs) => {
    setPrefs((prev) => ({ ...prev, [key]: !prev[key] }));
  };

  const handleSave = async () => {
    setLoading(true);
    setError(null);
    try {
      await saveConsent(prefs);
      router.push("/");
    } catch (e: any) {
      setError(e.message ?? "Tercihler kaydedilemedi");
    } finally {
      setLoading(false);
    }
  };

  const rows: { key: keyof typeof prefs; label: string; desc: string }[] = [
    {
      key: "push_notifications_enabled",
      label: "Anlık Bildirimler",
      desc: "Fiyat düşüşü ve kampanya bildirimleri alın",
    },
    {
      key: "email_notifications_enabled",
      label: "E-posta Bildirimleri",
      desc: "Haftalık fiyat raporu ve öneriler",
    },
    {
      key: "notify_on_price_drop",
      label: "Fiyat Düşüşü",
      desc: "Takip ettiğiniz ürünlerde fiyat düştüğünde",
    },
    {
      key: "notify_on_back_in_stock",
      label: "Stok Bildirimi",
      desc: "Tükenen ürünler tekrar satışa çıktığında",
    },
  ];

  return (
    <div className="min-h-[calc(100vh-4rem)] flex items-center justify-center px-4 py-16">
      <div className="w-full max-w-md space-y-8">
        {/* Header */}
        <div className="space-y-2">
          <h1 className="text-2xl font-bold text-gray-900">
            Hoş geldin{userName ? `, ${userName.split(" ")[0]}` : ""}!
          </h1>
          <p className="text-sm text-gray-500">
            İletişim tercihlerinizi belirleyin. Dilediğiniz zaman ayarlardan
            değiştirebilirsiniz.
          </p>
        </div>

        {error && (
          <div className="bg-danger/10 text-danger text-sm rounded-lg p-3 text-center">
            {error}
          </div>
        )}

        {/* Toggles */}
        <div className="space-y-3">
          {rows.map((row) => (
            <label
              key={row.key}
              className="flex items-center justify-between bg-gray-50 rounded-xl p-4 cursor-pointer hover:bg-gray-100 transition-colors"
            >
              <div className="flex-1 mr-4">
                <div className="text-sm font-semibold text-gray-900">
                  {row.label}
                </div>
                <div className="text-xs text-gray-500 mt-0.5">{row.desc}</div>
              </div>
              <button
                type="button"
                role="switch"
                aria-checked={prefs[row.key]}
                onClick={() => toggle(row.key)}
                className={`relative inline-flex h-6 w-11 items-center rounded-full transition-colors ${
                  prefs[row.key] ? "bg-brand" : "bg-gray-300"
                }`}
              >
                <span
                  className={`inline-block h-4 w-4 transform rounded-full bg-white transition-transform ${
                    prefs[row.key] ? "translate-x-6" : "translate-x-1"
                  }`}
                />
              </button>
            </label>
          ))}
        </div>

        {/* KVKK notice */}
        <p className="text-xs text-gray-400 leading-relaxed">
          6698 sayılı Kişisel Verilerin Korunması Kanunu kapsamında, kişisel
          verileriniz yalnızca hizmet sunumu amacıyla işlenmektedir.
          Tercihlerinizi istediğiniz zaman güncelleyebilirsiniz.
        </p>

        {/* Continue */}
        <button
          onClick={handleSave}
          disabled={loading}
          className="w-full bg-brand text-white rounded-lg py-3 px-4 text-sm font-semibold hover:bg-brand-dark transition-colors disabled:opacity-50"
        >
          {loading ? "Kaydediliyor..." : "Devam Et"}
        </button>
      </div>
    </div>
  );
}
