import Link from "next/link";
import { BreadcrumbSchema } from "@/components/seo/BreadcrumbSchema";

interface BreadcrumbItem {
  name: string;
  href: string;
}

export function Breadcrumb({ items }: { items: BreadcrumbItem[] }) {
  const allItems = [{ name: "Ana Sayfa", href: "/" }, ...items];

  return (
    <>
      <BreadcrumbSchema items={allItems} />
      <nav aria-label="Breadcrumb" className="text-sm text-gray-500">
        <ol className="flex items-center flex-wrap gap-1">
          {allItems.map((item, i) => (
            <li key={item.href} className="flex items-center">
              {i > 0 && <span className="mx-1 text-gray-300">/</span>}
              {i === allItems.length - 1 ? (
                <span className="text-gray-900 font-medium">{item.name}</span>
              ) : (
                <Link
                  href={item.href}
                  className="hover:text-brand transition-colors"
                >
                  {item.name}
                </Link>
              )}
            </li>
          ))}
        </ol>
      </nav>
    </>
  );
}
