import { NextRequest, NextResponse } from "next/server";

/**
 * Apple Sign-In callback endpoint.
 * Apple posts form data here after authentication.
 * In popup mode, this page just needs to exist and pass data back to the opener.
 */
export async function POST(request: NextRequest) {
  const formData = await request.formData();
  const code = formData.get("code") as string | null;
  const idToken = formData.get("id_token") as string | null;
  const state = formData.get("state") as string | null;
  const user = formData.get("user") as string | null;

  // Return a simple HTML page that sends the data back to the popup opener
  const html = `<!DOCTYPE html>
<html>
<head><title>Apple Sign-In</title></head>
<body>
<script>
  if (window.opener) {
    window.opener.postMessage({
      type: "apple-signin",
      id_token: ${JSON.stringify(idToken)},
      code: ${JSON.stringify(code)},
      user: ${JSON.stringify(user)}
    }, window.location.origin);
    window.close();
  }
</script>
</body>
</html>`;

  return new NextResponse(html, {
    headers: { "Content-Type": "text/html" },
  });
}
