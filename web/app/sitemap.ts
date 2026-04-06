export const dynamic = "force-dynamic";

import type { MetadataRoute } from "next";
import { getCategories, getCategoryProducts, filterDisplayable } from "@/lib/api";
import { productSlug } from "@/lib/slugify";
import { blogPosts } from "@/lib/blog";

const BASE = "https://prial.io";

export default async function sitemap(): Promise<MetadataRoute.Sitemap> {
  const entries: MetadataRoute.Sitemap = [
    {
      url: BASE,
      lastModified: new Date(),
      changeFrequency: "daily",
      priority: 1,
    },
    {
      url: `${BASE}/blog`,
      lastModified: new Date(),
      changeFrequency: "weekly",
      priority: 0.7,
    },
  ];

  // Blog posts
  for (const post of blogPosts) {
    entries.push({
      url: `${BASE}/blog/${post.slug}`,
      lastModified: new Date(post.date),
      changeFrequency: "monthly",
      priority: 0.6,
    });
  }

  // Categories + products + brands
  let categories: Awaited<ReturnType<typeof getCategories>> = [];
  try {
    categories = await getCategories(3600);
  } catch (e) {
    console.error("[sitemap] getCategories failed:", e);
  }

  const brands = new Set<string>();
  const seen = new Set<string>();

  // Add category URLs
  for (const cat of categories) {
    entries.push({
      url: `${BASE}/${cat.slug}`,
      lastModified: new Date(),
      changeFrequency: "hourly",
      priority: 0.8,
    });
  }

  // Fetch all category products in parallel (was sequential → timeout)
  const results = await Promise.allSettled(
    categories.map((cat) =>
      getCategoryProducts(cat.slug, 1, 50, "alarm_count", 3600).then(
        (raw) => ({ cat, products: filterDisplayable(raw) })
      )
    )
  );

  for (const result of results) {
    if (result.status !== "fulfilled") {
      console.error("[sitemap] getCategoryProducts failed:", result.reason);
      continue;
    }

    const { cat, products } = result.value;

    for (const p of products) {
      if (seen.has(p.id)) continue;
      seen.add(p.id);

      const catSlug = p.category_slug ?? cat.slug;
      const pSlug = productSlug(p.title, p.id);
      entries.push({
        url: `${BASE}/${catSlug}/${pSlug}`,
        lastModified: new Date(),
        changeFrequency: "hourly",
        priority: 0.9,
      });

      if (p.brand) brands.add(p.brand);
    }
  }

  // Brand pages
  for (const brand of brands) {
    entries.push({
      url: `${BASE}/marka/${brand.toLowerCase().replace(/\s+/g, "-")}`,
      lastModified: new Date(),
      changeFrequency: "daily",
      priority: 0.6,
    });
  }

  return entries;
}
