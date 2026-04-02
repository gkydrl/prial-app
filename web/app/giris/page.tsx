"use client";

import { useState, useEffect, useCallback } from "react";
import { useRouter } from "next/navigation";
import Image from "next/image";
import Script from "next/script";
import { socialLogin, isLoggedIn } from "@/lib/auth";

const API_BASE = process.env.NEXT_PUBLIC_API_BASE_URL ?? "https://prial-app-production.up.railway.app/api/v1";

export default function LoginPage() {
  const router = useRouter();
  const [loading, setLoading] = useState<"google" | "apple" | "email" | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");

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
      ux_mode: "popup",
    });
  }, [handleGoogleResponse]);

  // Email/password login
  const handleEmailLogin = async () => {
    if (!email || !password) {
      setError("E-posta ve şifre gerekli");
      return;
    }
    setLoading("email");
    setError(null);
    try {
      const res = await fetch(`${API_BASE}/auth/login`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ email, password }),
      });
      if (!res.ok) {
        const data = await res.json().catch(() => ({}));
        throw new Error(data.detail ?? "E-posta veya şifre hatalı");
      }
      const data = await res.json();
      localStorage.setItem("prial_access_token", data.access_token);
      localStorage.setItem("prial_refresh_token", data.refresh_token);
      router.push("/");
    } catch (e: any) {
      setError(e.message);
    } finally {
      setLoading(null);
    }
  };

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
        redirectURI: "https://prial.io/api/auth/apple/callback",
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
          <div className="text-center space-y-1">
            <Image
              src="/logo.png"
              alt="Prial"
              width={120}
              height={42}
              className="mx-auto"
              priority
            />
            <p className="text-sm text-gray-400">Akıllı Alışveriş Asistanı</p>
          </div>

          {/* Error */}
          {error && (
            <div className="bg-danger/10 text-danger text-sm rounded-lg p-3 text-center">
              {error}
            </div>
          )}

          {/* Email login form */}
          <form
            onSubmit={(e) => {
              e.preventDefault();
              handleEmailLogin();
            }}
            className="space-y-3"
          >
            <div>
              <label htmlFor="email" className="block text-sm font-medium text-gray-700 mb-1">
                E-posta
              </label>
              <input
                id="email"
                type="email"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                placeholder="ornek@email.com"
                autoComplete="email"
                className="w-full rounded-xl border border-gray-300 px-4 py-2.5 text-sm focus:outline-none focus:ring-2 focus:ring-brand focus:border-transparent"
              />
            </div>
            <div>
              <label htmlFor="password" className="block text-sm font-medium text-gray-700 mb-1">
                Şifre
              </label>
              <input
                id="password"
                type="password"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                placeholder="En az 8 karakter"
                autoComplete="current-password"
                className="w-full rounded-xl border border-gray-300 px-4 py-2.5 text-sm focus:outline-none focus:ring-2 focus:ring-brand focus:border-transparent"
              />
            </div>
            <button
              type="submit"
              disabled={!!loading}
              className="w-full bg-brand text-white rounded-xl py-2.5 px-4 text-sm font-semibold hover:bg-brand-dark transition-colors disabled:opacity-50"
            >
              {loading === "email" ? "Yükleniyor..." : "Giriş Yap"}
            </button>
          </form>

          {/* Divider */}
          <div className="flex items-center gap-3">
            <div className="flex-1 h-px bg-gray-200" />
            <span className="text-sm text-gray-400">veya</span>
            <div className="flex-1 h-px bg-gray-200" />
          </div>

          {/* Social buttons */}
          <div className="space-y-3">
            {/* Google button */}
            <button
              onClick={() => {
                const google = (window as any).google;
                if (google?.accounts?.id) {
                  google.accounts.id.prompt();
                }
              }}
              disabled={!!loading}
              className="w-full flex items-center justify-center gap-2.5 border border-gray-300 bg-white text-gray-700 rounded-xl py-2.5 px-4 text-sm font-medium hover:bg-gray-50 transition-colors disabled:opacity-50"
            >
              <svg className="w-5 h-5" viewBox="0 0 24 24">
                <path d="M22.56 12.25c0-.78-.07-1.53-.2-2.25H12v4.26h5.92a5.06 5.06 0 0 1-2.2 3.32v2.77h3.57c2.08-1.92 3.28-4.74 3.28-8.1z" fill="#4285F4"/>
                <path d="M12 23c2.97 0 5.46-.98 7.28-2.66l-3.57-2.77c-.98.66-2.23 1.06-3.71 1.06-2.86 0-5.29-1.93-6.16-4.53H2.18v2.84C3.99 20.53 7.7 23 12 23z" fill="#34A853"/>
                <path d="M5.84 14.09c-.22-.66-.35-1.36-.35-2.09s.13-1.43.35-2.09V7.07H2.18C1.43 8.55 1 10.22 1 12s.43 3.45 1.18 4.93l2.85-2.22.81-.62z" fill="#FBBC05"/>
                <path d="M12 5.38c1.62 0 3.06.56 4.21 1.64l3.15-3.15C17.45 2.09 14.97 1 12 1 7.7 1 3.99 3.47 2.18 7.07l3.66 2.84c.87-2.6 3.3-4.53 6.16-4.53z" fill="#EA4335"/>
              </svg>
              {loading === "google" ? "Yükleniyor..." : "Google ile Giriş Yap"}
            </button>

            {/* Apple button */}
            <button
              onClick={handleAppleLogin}
              disabled={!!loading}
              className="w-full flex items-center justify-center gap-2.5 border border-black bg-black text-white rounded-xl py-2.5 px-4 text-sm font-medium hover:bg-gray-900 transition-colors disabled:opacity-50"
            >
              <svg className="w-5 h-5" viewBox="0 0 24 24" fill="currentColor">
                <path d="M17.05 20.28c-.98.95-2.05.88-3.08.4-1.09-.5-2.08-.48-3.24 0-1.44.62-2.2.44-3.06-.4C2.79 15.25 3.51 7.59 9.05 7.31c1.35.07 2.29.74 3.08.8 1.18-.24 2.31-.93 3.57-.84 1.51.12 2.65.72 3.4 1.8-3.12 1.87-2.38 5.98.48 7.13-.57 1.5-1.31 2.99-2.54 4.09zM12.03 7.25c-.15-2.23 1.66-4.07 3.74-4.25.29 2.58-2.34 4.5-3.74 4.25z" />
              </svg>
              {loading === "apple" ? "Yükleniyor..." : "Apple ile Giriş Yap"}
            </button>
          </div>

          {/* Register link */}
          <p className="text-sm text-gray-500 text-center">
            Hesabın yok mu?{" "}
            <a href="/giris/kayit" className="text-brand font-semibold hover:underline">
              Kayıt ol
            </a>
          </p>

          {/* KVKK notice */}
          <p className="text-xs text-gray-400 text-left leading-relaxed">
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
