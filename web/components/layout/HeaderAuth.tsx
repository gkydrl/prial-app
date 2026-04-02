"use client";

import { useState, useEffect } from "react";
import Link from "next/link";
import { isLoggedIn, clearTokens, fetchMe } from "@/lib/auth";

export function HeaderAuth() {
  const [loggedIn, setLoggedIn] = useState(false);
  const [userName, setUserName] = useState<string | null>(null);
  const [menuOpen, setMenuOpen] = useState(false);

  useEffect(() => {
    if (isLoggedIn()) {
      setLoggedIn(true);
      fetchMe()
        .then((user) => setUserName(user.full_name))
        .catch(() => {
          clearTokens();
          setLoggedIn(false);
        });
    }
  }, []);

  const handleLogout = () => {
    clearTokens();
    setLoggedIn(false);
    setUserName(null);
    setMenuOpen(false);
    window.location.href = "/";
  };

  if (loggedIn) {
    return (
      <div className="hidden sm:flex items-center gap-5">
        <Link
          href="/blog"
          className="text-sm text-gray-600 hover:text-brand transition-colors"
        >
          Blog
        </Link>
        <Link
          href="/kampanyalar"
          className="text-sm text-gray-600 hover:text-brand transition-colors"
        >
          Kampanyalar
        </Link>
        <div className="relative">
          <button
            onClick={() => setMenuOpen(!menuOpen)}
            aria-label="Hesap menüsü"
            aria-expanded={menuOpen}
            aria-haspopup="true"
            className="flex items-center gap-1.5 text-sm font-medium text-gray-700 hover:text-brand transition-colors"
          >
            <div className="w-7 h-7 rounded-full bg-brand text-white flex items-center justify-center text-xs font-semibold">
              {userName ? userName.charAt(0).toUpperCase() : "P"}
            </div>
            <svg className="w-4 h-4 text-gray-400" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 9l-7 7-7-7" />
            </svg>
          </button>
          {menuOpen && (
            <>
              <div className="fixed inset-0 z-40" onClick={() => setMenuOpen(false)} />
              <div className="absolute right-0 top-full mt-2 w-48 bg-white border border-gray-200 rounded-xl shadow-lg py-1 z-50">
                <div className="px-4 py-2 border-b border-gray-100">
                  <p className="text-sm font-medium text-gray-900 truncate">
                    {userName ?? "Hesabım"}
                  </p>
                </div>
                <Link
                  href="/profil"
                  onClick={() => setMenuOpen(false)}
                  className="block px-4 py-2 text-sm text-gray-700 hover:bg-gray-50"
                >
                  Profil
                </Link>
                <button
                  onClick={handleLogout}
                  className="w-full text-left px-4 py-2 text-sm text-danger hover:bg-danger/5"
                >
                  Çıkış Yap
                </button>
              </div>
            </>
          )}
        </div>
      </div>
    );
  }

  return (
    <div className="hidden sm:flex items-center gap-4">
      <Link
        href="/blog"
        className="text-sm text-gray-600 hover:text-brand transition-colors"
      >
        Blog
      </Link>
      <Link
        href="/giris"
        className="inline-flex items-center gap-1.5 bg-brand-dark text-white text-sm font-medium px-4 py-2 rounded-lg hover:bg-brand transition-colors"
      >
        Giriş Yap
      </Link>
    </div>
  );
}
