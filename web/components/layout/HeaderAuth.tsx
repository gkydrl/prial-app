"use client";

import { useState, useEffect } from "react";
import Link from "next/link";
import { isLoggedIn, clearTokens, fetchMe } from "@/lib/auth";

export function HeaderAuth() {
  const [loggedIn, setLoggedIn] = useState(false);
  const [userName, setUserName] = useState<string | null>(null);

  useEffect(() => {
    if (isLoggedIn()) {
      setLoggedIn(true);
      fetchMe()
        .then((user) => setUserName(user.full_name))
        .catch(() => {
          // Token expired
          clearTokens();
          setLoggedIn(false);
        });
    }
  }, []);

  const handleLogout = () => {
    clearTokens();
    setLoggedIn(false);
    setUserName(null);
    window.location.href = "/";
  };

  if (loggedIn) {
    return (
      <div className="hidden sm:flex items-center gap-3">
        <span className="text-sm text-gray-700 font-medium">
          {userName ?? "Hesabım"}
        </span>
        <button
          onClick={handleLogout}
          className="text-sm text-gray-500 hover:text-red-600 transition-colors"
        >
          Çıkış
        </button>
      </div>
    );
  }

  return (
    <Link
      href="/giris"
      className="hidden sm:inline-flex items-center gap-1.5 bg-brand-dark text-white text-sm font-medium px-4 py-2 rounded-lg hover:bg-brand transition-colors"
    >
      Giriş Yap
    </Link>
  );
}
