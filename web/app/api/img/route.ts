import { NextRequest, NextResponse } from "next/server";

const REFERER_MAP: Record<string, string> = {
  "cdn.dsmcdn.com": "https://www.trendyol.com/",
  "trendyol.com": "https://www.trendyol.com/",
  "hepsiburada.net": "https://www.hepsiburada.com/",
  "hepsiburada.com": "https://www.hepsiburada.com/",
  mediamarkt: "https://www.mediamarkt.com.tr/",
};

function getReferer(url: string): string | undefined {
  for (const [domain, referer] of Object.entries(REFERER_MAP)) {
    if (url.includes(domain)) return referer;
  }
  return undefined;
}

export async function GET(request: NextRequest) {
  const url = request.nextUrl.searchParams.get("url");

  if (!url) {
    return NextResponse.json({ error: "Missing url parameter" }, { status: 400 });
  }

  try {
    new URL(url);
  } catch {
    return NextResponse.json({ error: "Invalid url" }, { status: 400 });
  }

  try {
    const headers: Record<string, string> = {
      "User-Agent":
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    };

    const referer = getReferer(url);
    if (referer) {
      headers["Referer"] = referer;
    }

    const response = await fetch(url, { headers });

    if (!response.ok) {
      return NextResponse.json(
        { error: `Upstream error: ${response.status}` },
        { status: 502 }
      );
    }

    const contentType = response.headers.get("content-type") ?? "image/jpeg";
    const buffer = await response.arrayBuffer();

    return new NextResponse(buffer, {
      headers: {
        "Content-Type": contentType,
        "Cache-Control": "public, max-age=86400, stale-while-revalidate=604800",
      },
    });
  } catch {
    return NextResponse.json({ error: "Failed to fetch image" }, { status: 500 });
  }
}
