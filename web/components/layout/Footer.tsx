import Link from "next/link";
import Image from "next/image";

export default function Footer() {
  return (
    <footer className="bg-gray-50 border-t border-gray-200 mt-16">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-12">
        <div className="grid grid-cols-1 md:grid-cols-4 gap-8">
          {/* Brand */}
          <div className="flex flex-col items-center text-center">
            <Link href="/">
              <Image src="/logo.png" alt="Prial" width={72} height={26} />
            </Link>
            <p className="mt-2 text-sm text-gray-500">
              Akıllı Alışveriş Asistanı
            </p>
          </div>

          {/* Categories */}
          <div>
            <h3 className="text-sm font-semibold text-gray-900 mb-3">
              Popüler Kategoriler
            </h3>
            <ul className="space-y-2 text-sm text-gray-500">
              <li>
                <Link href="/akilli-telefon" className="hover:text-brand">
                  Akıllı Telefon
                </Link>
              </li>
              <li>
                <Link href="/laptop" className="hover:text-brand">
                  Laptop
                </Link>
              </li>
              <li>
                <Link href="/tablet" className="hover:text-brand">
                  Tablet
                </Link>
              </li>
              <li>
                <Link href="/kulaklik" className="hover:text-brand">
                  Kulaklık
                </Link>
              </li>
            </ul>
          </div>

          {/* Links */}
          <div>
            <h3 className="text-sm font-semibold text-gray-900 mb-3">
              Prial
            </h3>
            <ul className="space-y-2 text-sm text-gray-500">
              <li>
                <Link href="/blog" className="hover:text-brand">
                  Blog
                </Link>
              </li>
              <li>
                <a
                  href="https://apps.apple.com/tr/app/prial/id6760142538"
                  target="_blank"
                  rel="noopener noreferrer"
                  className="hover:text-brand"
                >
                  iOS Uygulaması
                </a>
              </li>
            </ul>
          </div>

          {/* Legal */}
          <div>
            <h3 className="text-sm font-semibold text-gray-900 mb-3">Yasal</h3>
            <ul className="space-y-2 text-sm text-gray-500">
              <li>
                <Link href="/gizlilik" className="hover:text-brand">
                  Gizlilik Politikası
                </Link>
              </li>
              <li>
                <Link href="/kullanim-kosullari" className="hover:text-brand">
                  Kullanım Koşulları
                </Link>
              </li>
            </ul>
          </div>
        </div>

        <div className="mt-8 pt-8 border-t border-gray-200 text-center text-sm text-gray-400">
          © {new Date().getFullYear()} Prial. Tüm hakları saklıdır.
        </div>
      </div>
    </footer>
  );
}
