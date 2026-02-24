export interface PreviewResult {
  title: string;
  current_price: number;
  image_url: string | null;
}

const FETCH_HEADERS: Record<string, string> = {
  'User-Agent':
    'Mozilla/5.0 (iPhone; CPU iPhone OS 17_0 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.0 Mobile/15E148 Safari/604.1',
  Accept: 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
  'Accept-Language': 'tr-TR,tr;q=0.9,en;q=0.8',
};

export async function fetchProductPreview(url: string): Promise<PreviewResult> {
  const response = await fetch(url, { headers: FETCH_HEADERS });
  if (!response.ok) throw new Error(`HTTP ${response.status}`);
  const html = await response.text();

  const result = parseLdJson(html) ?? parseInitialState(html);
  if (!result) throw new Error('Ürün bilgileri bulunamadı');
  return result;
}

/** <script type="application/ld+json"> içindeki Product/ProductGroup verisini parse eder */
function parseLdJson(html: string): PreviewResult | null {
  const scriptRe = /<script[^>]+type="application\/ld\+json"[^>]*>([\s\S]*?)<\/script>/gi;
  let match: RegExpExecArray | null;

  while ((match = scriptRe.exec(html)) !== null) {
    try {
      const data = JSON.parse(match[1]);
      const items: any[] = Array.isArray(data) ? data : [data];

      for (const item of items) {
        const type = item?.['@type'];
        if (type !== 'Product' && type !== 'ProductGroup') continue;

        // Fiyat: offers.price → offers.lowPrice → hasVariant[0].offers.price
        const offers = item.offers ?? {};
        let rawPrice =
          offers.price ??
          offers.lowPrice ??
          item.hasVariant?.[0]?.offers?.price ??
          '';
        const price = parseFloat(rawPrice.toString().replace(',', '.'));
        if (!price || isNaN(price)) continue;

        // Görsel: string | string[] | ImageObject { contentUrl: string[] }
        const imageRaw = item.image;
        let image_url: string | null = null;
        if (typeof imageRaw === 'string') {
          image_url = imageRaw;
        } else if (Array.isArray(imageRaw)) {
          image_url = imageRaw[0] ?? null;
        } else if (imageRaw && typeof imageRaw === 'object') {
          const contentUrl = imageRaw.contentUrl;
          image_url = Array.isArray(contentUrl)
            ? contentUrl[0] ?? null
            : contentUrl ?? null;
        }

        return { title: item.name ?? '', current_price: price, image_url };
      }
    } catch {
      // Geçersiz JSON — sonraki script'i dene
    }
  }
  return null;
}

/** window.__PRODUCT_DETAIL_APP_INITIAL_STATE__ verisini parse eder */
function parseInitialState(html: string): PreviewResult | null {
  const re =
    /window\.__PRODUCT_DETAIL_APP_INITIAL_STATE__\s*=\s*(\{[\s\S]*?\});\s*(?:window\.|<\/script>)/;
  const match = re.exec(html);
  if (!match) return null;

  try {
    const data = JSON.parse(match[1]);
    const product = data?.product ?? {};
    const priceInfo = product?.priceInfo ?? {};

    const rawPrice = priceInfo.discountedPrice ?? priceInfo.price;
    if (!rawPrice) return null;

    const current_price = parseFloat(rawPrice.toString().replace(',', '.'));
    if (isNaN(current_price)) return null;

    const images: string[] = product.images ?? [];
    const firstImg = images[0] ?? null;
    const image_url = firstImg
      ? firstImg.startsWith('http')
        ? firstImg
        : `https://cdn.dsmcdn.com${firstImg}`
      : null;

    return { title: product.name ?? '', current_price, image_url };
  } catch {
    return null;
  }
}
