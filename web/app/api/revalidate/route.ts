import { revalidateTag } from "next/cache";
import { NextRequest, NextResponse } from "next/server";

export async function POST(request: NextRequest) {
  const secret = request.headers.get("x-revalidate-secret");

  if (secret !== process.env.REVALIDATE_SECRET) {
    return NextResponse.json({ error: "Unauthorized" }, { status: 401 });
  }

  try {
    const body = await request.json();

    // Support both single tag and array of tags
    const tags: string[] = body.tags
      ? body.tags
      : body.tag
        ? [body.tag]
        : [];

    if (tags.length === 0) {
      return NextResponse.json(
        { error: "Missing tag or tags parameter" },
        { status: 400 }
      );
    }

    for (const tag of tags) {
      if (typeof tag === "string") {
        revalidateTag(tag, "default");
      }
    }

    return NextResponse.json({ revalidated: true, tags });
  } catch {
    return NextResponse.json(
      { error: "Failed to revalidate" },
      { status: 500 }
    );
  }
}
