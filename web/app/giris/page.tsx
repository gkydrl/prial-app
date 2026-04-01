"use client";

import { useState, useEffect, useCallback } from "react";
import { useRouter } from "next/navigation";
import Image from "next/image";
import Script from "next/script";
import { socialLogin, isLoggedIn } from "@/lib/auth";

export default function LoginPage() {
  const router = useRouter();
  const [loading, setLoading] = useState<"google" | "apple" | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (isLoggedIn()) {
      router.replace("/");
    }
  }, [router]);

  // Google Sign-In callback
  const handleGoogleResponse = useCallback(
    async (response: { credential?: string }) => {
      if (!response.credential) return;
      setLoading("google");
      setError(null);
      try {
        const result = await socialLogin("google", response.credential);
        if (result.needs_consent) {
          router.push("/giris/tercihler");
        } else {
          router.push("/");
        }
      } catch (e: any) {
        setError(e.message ?? "Google ile giriş başarısız");
      } finally {
        setLoading(null);
      }
    },
    [router]
  );

  // Initialize Google Sign-In when the script loads
  const initializeGoogle = useCallback(() => {
    const clientId = process.env.NEXT_PUBLIC_GOOGLE_CLIENT_ID;
    if (!clientId || typeof window === "undefined") return;

    const google = (window as any).google;
    if (!google?.accounts?.id) return;

    google.accounts.id.initialize({
      client_id: clientId,
      callback: handleGoogleResponse,
    });

    const buttonDiv = document.getElementById("google-signin-btn");
    if (buttonDiv) {
      google.accounts.id.renderButton(buttonDiv, {
        type: "standard",
        shape: "rectangular",
        theme: "outline",
        size: "large",
        text: "continue_with",
        locale: "tr",
        width: 360,
      });
    }
  }, [handleGoogleResponse]);

  // Apple Sign-In
  const handleAppleLogin = async () => {
    setLoading("apple");
    setError(null);
    try {
      const AppleID = (window as any).AppleID;
      if (!AppleID) {
        setError("Apple Sign-In yüklenemedi");
        return;
      }

      AppleID.auth.init({
        clientId: "io.prial.web.signin",
        scope: "name email",
        redirectURI: `${window.location.origin}/api/auth/apple/callback`,
        usePopup: true,
      });

      const response = await AppleID.auth.signIn();
      const idToken = response.authorization?.id_token;
      if (!idToken) return;

      const fullName = response.user
        ? [response.user.name?.firstName, response.user.name?.lastName]
            .filter(Boolean)
            .join(" ")
        : undefined;

      const result = await socialLogin("apple", idToken, fullName || undefined);
      if (result.needs_consent) {
        router.push("/giris/tercihler");
      } else {
        router.push("/");
      }
    } catch (e: any) {
      if (e.error !== "popup_closed_by_user") {
        setError(e.message ?? "Apple ile giriş başarısız");
      }
    } finally {
      setLoading(null);
    }
  };

  return (
    <>
      {/* Google Identity Services script */}
      <Script
        src="https://accounts.google.com/gsi/client"
        strategy="afterInteractive"
        onLoad={initializeGoogle}
      />
      {/* Apple Sign-In JS */}
      <Script
        src="https://appleid.cdn-apple.com/appleauth/static/jsapi/appleid/1/en_US/appleid.auth.js"
        strategy="afterInteractive"
      />

      <div className="min-h-[calc(100vh-4rem)] flex items-center justify-center px-4 py-16">
        <div className="w-full max-w-sm space-y-8">
          {/* Logo */}
          <div className="text-center space-y-2">
            <Image
              src="/logo.png"
              alt="Prial"
              width={120}
              height={42}
              className="mx-auto"
              priority
            />
            <h1 className="text-2xl font-bold text-gray-900">Giriş Yap</h1>
            <p className="text-sm text-gray-500">
              Kampanya talep etmek için giriş yapın
            </p>
          </div>

          {/* Error */}
          {error && (
            <div className="bg-red-50 text-red-600 text-sm rounded-lg p-3 text-center">
              {error}
            </div>
          )}

          {/* Social buttons */}
          <div className="space-y-3">
            {/* Google button rendered by GIS */}
            <div id="google-signin-btn" className="flex justify-center" />

            {/* Apple button */}
            <button
              onClick={handleAppleLogin}
              disabled={!!loading}
              className="w-full flex items-center justify-center gap-2.5 bg-black text-white rounded-lg py-3 px-4 text-sm font-medium hover:bg-gray-900 transition-colors disabled:opacity-50"
            >
              <svg className="w-5 h-5" viewBox="0 0 24 24" fill="currentColor">
                <path d="M17.05 20.28c-.98.95-2.05.88-3.08.4-1.09-.5-2.08-.48-3.24 0-1.44.62-2.2.44-3.06-.4C2.79 15.25 3.51 7.59 9.05 7.31c1.35.07 2.29.74 3.08.8 1.18-.24 2.31-.93 3.57-.84 1.51.12 2.65.72 3.4 1.8-3.12 1.87-2.38 5.98.48 7.13-.57 1.5-1.31 2.99-2.54 4.09zM12.03 7.25c-.15-2.23 1.66-4.07 3.74-4.25.29 2.58-2.34 4.5-3.74 4.25z" />
              </svg>
              {loading === "apple" ? "Yükleniyor..." : "Apple ile Giriş Yap"}
            </button>
          </div>

          {/* KVKK notice */}
          <p className="text-xs text-gray-400 text-center leading-relaxed">
            Giriş yaparak{" "}
            <a href="/gizlilik" className="text-brand underline">
              Gizlilik Politikası
            </a>
            {"'nı ve "}
            <a href="/kullanim-kosullari" className="text-brand underline">
              Kullanım Koşulları
            </a>
            {"'nı kabul etmiş olursunuz. Kişisel verileriniz 6698 sayılı KVKK kapsamında korunmaktadır."}
          </p>
        </div>
      </div>
    </>
  );
}
