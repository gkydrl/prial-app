export function OrganizationSchema() {
  const schema = {
    "@context": "https://schema.org",
    "@type": "Organization",
    name: "Prial",
    url: "https://prial.io",
    logo: "https://prial.io/icon.png",
    description:
      "Fiyat karşılaştırma ve takip platformu. Trendyol, Hepsiburada, Amazon ve daha fazlasında en ucuz fiyatı bul.",
    sameAs: ["https://apps.apple.com/app/prial"],
    contactPoint: {
      "@type": "ContactPoint",
      contactType: "customer support",
      availableLanguage: "Turkish",
    },
  };

  return (
    <script
      type="application/ld+json"
      dangerouslySetInnerHTML={{ __html: JSON.stringify(schema) }}
    />
  );
}
