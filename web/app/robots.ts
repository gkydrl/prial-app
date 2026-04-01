import type { MetadataRoute } from "next";

export default function robots(): MetadataRoute.Robots {
  return {
    rules: [
      {
        userAgent: "*",
        allow: "/",
        disallow: ["/api/", "/ara", "/*?sort=", "/*?page="],
      },
    ],
    sitemap: "https://prial.io/sitemap.xml",
  };
}
