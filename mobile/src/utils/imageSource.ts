/**
 * Trendyol CDN (cdn.dsmcdn.com) ve diğer mağaza CDN'leri,
 * doğrudan erişimde Referer header'ı görmezse 403 döner.
 * Bu fonksiyon URL'e göre uygun headers objesini döner.
 */
export function imageSource(url: string | null | undefined) {
  if (!url) return undefined;

  // Akakçe'nin kendi CDN'inden gelen görseller watermark/logo içerir, sadece bunları filtrele
  // Akakçe üzerinden gelen ama başka CDN'lerde barınan gerçek ürün görselleri etkilenmez
  if (url.includes('akakce')) return undefined;

  const headers: Record<string, string> = {};

  if (url.includes('cdn.dsmcdn.com') || url.includes('trendyol.com')) {
    headers['Referer'] = 'https://www.trendyol.com/';
  } else if (url.includes('hepsiburada.net') || url.includes('hepsiburada.com')) {
    headers['Referer'] = 'https://www.hepsiburada.com/';
  } else if (url.includes('mediamarkt')) {
    headers['Referer'] = 'https://www.mediamarkt.com.tr/';
  } else if (url.includes('amazon') || url.includes('m.media-amazon')) {
    headers['Referer'] = 'https://www.amazon.com.tr/';
  } else if (url.includes('n11.com')) {
    headers['Referer'] = 'https://www.n11.com/';
  }

  return Object.keys(headers).length > 0 ? { uri: url, headers } : { uri: url };
}
