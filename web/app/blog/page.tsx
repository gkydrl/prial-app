import type { Metadata } from "next";
import Link from "next/link";
import { blogPosts } from "@/lib/blog";

export const metadata: Metadata = {
  title: "Blog - Akıllı Alışveriş Rehberi",
  description:
    "Fiyat takibi, kampanya rehberleri ve akıllı alışveriş ipuçları. Prial blog ile bilinçli tüketici olun.",
  twitter: {
    card: "summary_large_image",
    title: "Blog - Akıllı Alışveriş Rehberi",
    description:
      "Fiyat takibi, kampanya rehberleri ve akıllı alışveriş ipuçları.",
  },
  alternates: {
    canonical: "https://prial.io/blog",
  },
};

export default function BlogPage() {
  return (
    <div className="max-w-4xl mx-auto px-4 sm:px-6 lg:px-8 py-10">
      <h1 className="text-3xl font-bold text-gray-900">Blog</h1>
      <p className="mt-2 text-gray-500">
        Akıllı alışveriş ipuçları, fiyat takibi rehberleri ve daha fazlası.
      </p>

      <div className="mt-10 space-y-8">
        {blogPosts.map((post) => (
          <article
            key={post.slug}
            className="border border-gray-200 rounded-xl p-6 hover:shadow-md hover:border-brand/30 transition-all"
          >
            <Link href={`/blog/${post.slug}`}>
              <div className="flex items-center gap-3 text-sm text-gray-500 mb-3">
                <time dateTime={post.date}>
                  {new Date(post.date).toLocaleDateString("tr-TR", {
                    year: "numeric",
                    month: "long",
                    day: "numeric",
                  })}
                </time>
                <span>&middot;</span>
                <span>{post.readTime} okuma</span>
              </div>
              <h2 className="text-xl font-semibold text-gray-900 hover:text-brand transition-colors">
                {post.title}
              </h2>
              <p className="mt-2 text-gray-600 text-sm leading-relaxed">
                {post.description}
              </p>
              <span className="inline-block mt-4 text-sm font-medium text-brand">
                Devamını oku &rarr;
              </span>
            </Link>
          </article>
        ))}
      </div>
    </div>
  );
}
