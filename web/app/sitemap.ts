export const dynamic = "force-dynamic";

import type { MetadataRoute } from "next";
import { getCategories, getCategoryProducts, filterDisplayable } from "@/lib/api";
import { productSlug } from "@/lib/slugify";
import { blogPosts } from "@/lib/blog";

const BASE = "https://prial.io";
const PRODUCTS_PER_SITEMAP = 1000;

export async function generateSitemaps() {
  // Estimate total product count from categories
  let totalProducts = 0;
  try {
    const categories = await getCategories(3600);
    totalProducts = categories.reduce((sum, c) => sum + (c.product_count ?? 0), 0);
  } catch {
    totalProducts = 200;
  }

  const sitemapCount = Math.max(1, Math.ceil(totalProducts / PRODUCTS_PER_SITEMAP));
  // id 0 = static pages + categories + blog + brands
  // id 1..n = product pages
  return Array.from({ length: sitemapCount + 1 }, (_, i) => ({ id: i }));
}

export default async function sitemap({
  id,
}: {
  id: number;
}): Promise<MetadataRoute.Sitemap> {
  // Sitemap 0: static pages, categories, blog, brands
  if (id === 0) {
    return await buildStaticSitemap();
  }

  // Sitemap 1+: product pages
  return await buildProductSitemap(id - 1);
}

async function buildStaticSitemap(): Promise<MetadataRoute.Sitemap> {
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

  // Categories
  try {
    const categories = await getCategories(3600);
    const brands = new Set<string>();

    for (const cat of categories) {
      entries.push({
        url: `${BASE}/${cat.slug}`,
        lastModified: new Date(),
        changeFrequency: "hourly",
        priority: 0.8,
      });
    }

    // Collect brands from first category page of each category
    for (const cat of categories) {
      try {
        const products = await getCategoryProducts(cat.slug, 1, 48, "alarm_count", 3600);
        for (const p of products) {
          if (p.brand) brands.add(p.brand);
        }
      } catch {
        // skip
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
  } catch {
    // skip on error
  }

  return entries;
}

async function buildProductSitemap(page: number): Promise<MetadataRoute.Sitemap> {
  const entries: MetadataRoute.Sitemap = [];

  try {
    const categories = await getCategories(3600);
    let allProducts: Array<{ title: string; id: string; category_slug: string | null }> = [];

    for (const cat of categories) {
      try {
        const rawProducts = await getCategoryProducts(cat.slug, 1, 5000, "alarm_count", 3600);
        const products = filterDisplayable(rawProducts);
        for (const p of products) {
          allProducts.push({
            title: p.title,
            id: p.id,
            category_slug: p.category_slug ?? cat.slug,
          });
        }
      } catch {
        // skip
      }
    }

    // Deduplicate by product id
    const seen = new Set<string>();
    allProducts = allProducts.filter((p) => {
      if (seen.has(p.id)) return false;
      seen.add(p.id);
      return true;
    });

    // Slice for this sitemap page
    const start = page * PRODUCTS_PER_SITEMAP;
    const slice = allProducts.slice(start, start + PRODUCTS_PER_SITEMAP);

    for (const p of slice) {
      const catSlug = p.category_slug ?? "urun";
      const pSlug = productSlug(p.title, p.id);
      entries.push({
        url: `${BASE}/${catSlug}/${pSlug}`,
        lastModified: new Date(),
        changeFrequency: "hourly",
        priority: 0.9,
      });
    }
  } catch {
    // skip on error
  }

  return entries;
}
