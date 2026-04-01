import Link from "next/link";
import Image from "next/image";
import { SearchBar } from "./SearchBar";
import { HeaderAuth } from "./HeaderAuth";

export default function Header() {
  return (
    <header className="sticky top-0 z-50 bg-white border-b border-gray-200">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <div className="flex items-center justify-between h-16 gap-4">
          {/* Logo */}
          <Link href="/" className="flex-shrink-0">
            <Image
              src="/logo.png"
              alt="Prial"
              width={80}
              height={28}
              priority
            />
          </Link>

          {/* Search */}
          <div className="flex-1 max-w-xl">
            <SearchBar />
          </div>

          {/* Right side */}
          <div className="flex items-center gap-4">
            <Link
              href="/blog"
              className="hidden sm:inline-flex text-sm text-gray-600 hover:text-brand transition-colors"
            >
              Blog
            </Link>
            <HeaderAuth />
          </div>
        </div>
      </div>
    </header>
  );
}
