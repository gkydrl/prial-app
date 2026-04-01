import { notFound } from "next/navigation";
import type { Metadata } from "next";
import Link from "next/link";
import { blogPosts, getBlogPost } from "@/lib/blog";
import { Breadcrumb } from "@/components/layout/Breadcrumb";
import { ArticleSchema } from "@/components/seo/ArticleSchema";

interface Props {
  params: Promise<{ slug: string }>;
}

export async function generateStaticParams() {
  return blogPosts.map((post) => ({ slug: post.slug }));
}

export async function generateMetadata({ params }: Props): Promise<Metadata> {
  const { slug } = await params;
  const post = getBlogPost(slug);
  if (!post) return {};

  return {
    title: post.title,
    description: post.description,
    openGraph: {
      title: post.title,
      description: post.description,
      type: "article",
      publishedTime: post.date,
      url: `https://prial.io/blog/${slug}`,
      siteName: "Prial",
      locale: "tr_TR",
    },
    twitter: {
      card: "summary_large_image",
      title: post.title,
      description: post.description,
    },
    alternates: {
      canonical: `https://prial.io/blog/${slug}`,
    },
  };
}

export default async function BlogPostPage({ params }: Props) {
  const { slug } = await params;
  const post = getBlogPost(slug);
  if (!post) notFound();

  return (
    <div className="max-w-3xl mx-auto px-4 sm:px-6 lg:px-8 py-10">
      <ArticleSchema
        title={post.title}
        description={post.description}
        slug={post.slug}
        date={post.date}
      />

      <Breadcrumb
        items={[
          { name: "Blog", href: "/blog" },
          { name: post.title, href: `/blog/${post.slug}` },
        ]}
      />

      <article className="mt-8">
        <header>
          <div className="flex items-center gap-3 text-sm text-gray-500 mb-4">
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
          <h1 className="text-3xl font-bold text-gray-900">{post.title}</h1>
          <p className="mt-3 text-lg text-gray-600">{post.description}</p>
        </header>

        <div className="mt-10 prose prose-gray max-w-none">
          {post.content.split("\n\n").map((paragraph, i) => {
            if (paragraph.startsWith("## ")) {
              return (
                <h2
                  key={i}
                  className="text-xl font-semibold text-gray-900 mt-8 mb-4"
                >
                  {paragraph.replace("## ", "")}
                </h2>
              );
            }
            if (paragraph.startsWith("---")) {
              return <hr key={i} className="my-8 border-gray-200" />;
            }
            return (
              <p key={i} className="text-gray-600 leading-relaxed mb-4">
                {paragraph}
              </p>
            );
          })}
        </div>

        {/* CTA */}
        <div className="mt-12 p-6 bg-gradient-to-r from-brand to-brand-dark rounded-2xl text-white text-center">
          <h3 className="text-lg font-bold">
            Prial ile Akıllı Alışverişe Başla
          </h3>
          <p className="mt-2 text-blue-100 text-sm">
            Fiyat takibi, mağaza karşılaştırması ve kampanya talepleri — hepsi
            tek uygulamada.
          </p>
          <div className="mt-4 flex justify-center gap-3">
            <a
              href="https://apps.apple.com/tr/app/prial-fiyat-takip-asistani/id6746519498"
              target="_blank"
              rel="noopener noreferrer"
              className="inline-flex items-center gap-2 bg-white text-brand px-5 py-2.5 rounded-lg font-semibold text-sm hover:bg-blue-50 transition-colors"
            >
              App Store
            </a>
          </div>
        </div>

        {/* Back to blog */}
        <div className="mt-8">
          <Link
            href="/blog"
            className="text-sm font-medium text-brand hover:underline"
          >
            &larr; Tüm yazılar
          </Link>
        </div>
      </article>
    </div>
  );
}
