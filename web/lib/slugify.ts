const TURKISH_MAP: Record<string, string> = {
  ş: "s",
  Ş: "S",
  ğ: "g",
  Ğ: "G",
  ü: "u",
  Ü: "U",
  ı: "i",
  İ: "I",
  ö: "o",
  Ö: "O",
  ç: "c",
  Ç: "C",
};

export function slugify(text: string): string {
  return text
    .replace(/[şŞğĞüÜıİöÖçÇ]/g, (char) => TURKISH_MAP[char] || char)
    .toLowerCase()
    .replace(/[^a-z0-9]+/g, "-")
    .replace(/^-+|-+$/g, "");
}

export function productSlug(title: string, id: string): string {
  const slug = slugify(title);
  const shortId = id.replace(/-/g, "").slice(0, 8);
  return `${slug}-${shortId}`;
}

export function extractShortId(slug: string): string {
  const parts = slug.split("-");
  return parts[parts.length - 1];
}
