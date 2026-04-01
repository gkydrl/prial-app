import Link from "next/link";

interface PaginationProps {
  currentPage: number;
  totalPages: number;
  baseHref: string;
}

export function Pagination({
  currentPage,
  totalPages,
  baseHref,
}: PaginationProps) {
  const pages = getPageNumbers(currentPage, totalPages);
  const separator = baseHref.includes("?") ? "&" : "?";

  return (
    <nav className="mt-8 flex justify-center items-center gap-1" aria-label="Sayfalama">
      {currentPage > 1 && (
        <Link
          href={`${baseHref}${separator}page=${currentPage - 1}`}
          className="px-3 py-2 text-sm rounded-lg border border-gray-200 text-gray-600 hover:bg-gray-50"
        >
          Önceki
        </Link>
      )}

      {pages.map((p, i) =>
        p === "..." ? (
          <span key={`ellipsis-${i}`} className="px-2 text-gray-400">
            ...
          </span>
        ) : (
          <Link
            key={p}
            href={`${baseHref}${separator}page=${p}`}
            className={`px-3 py-2 text-sm rounded-lg ${
              p === currentPage
                ? "bg-brand text-white font-medium"
                : "border border-gray-200 text-gray-600 hover:bg-gray-50"
            }`}
          >
            {p}
          </Link>
        )
      )}

      {currentPage < totalPages && (
        <Link
          href={`${baseHref}${separator}page=${currentPage + 1}`}
          className="px-3 py-2 text-sm rounded-lg border border-gray-200 text-gray-600 hover:bg-gray-50"
        >
          Sonraki
        </Link>
      )}
    </nav>
  );
}

function getPageNumbers(
  current: number,
  total: number
): (number | "...")[] {
  if (total <= 7) {
    return Array.from({ length: total }, (_, i) => i + 1);
  }

  const pages: (number | "...")[] = [1];

  if (current > 3) pages.push("...");

  const start = Math.max(2, current - 1);
  const end = Math.min(total - 1, current + 1);
  for (let i = start; i <= end; i++) {
    pages.push(i);
  }

  if (current < total - 2) pages.push("...");

  pages.push(total);

  return pages;
}
