interface ArticleSchemaProps {
  title: string;
  description: string;
  slug: string;
  date: string;
}

export function ArticleSchema({ title, description, slug, date }: ArticleSchemaProps) {
  const schema = {
    "@context": "https://schema.org",
    "@type": "Article",
    headline: title,
    description,
    datePublished: date,
    dateModified: date,
    url: `https://www.prial.io/blog/${slug}`,
    author: {
      "@type": "Organization",
      name: "Prial",
      url: "https://www.prial.io",
    },
    publisher: {
      "@type": "Organization",
      name: "Prial",
      url: "https://www.prial.io",
      logo: {
        "@type": "ImageObject",
        url: "https://www.prial.io/icon.png",
      },
    },
    mainEntityOfPage: {
      "@type": "WebPage",
      "@id": `https://www.prial.io/blog/${slug}`,
    },
    inLanguage: "tr",
  };

  return (
    <script
      type="application/ld+json"
      dangerouslySetInnerHTML={{ __html: JSON.stringify(schema) }}
    />
  );
}
