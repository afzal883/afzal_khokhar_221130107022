import { NextResponse } from "next/server";
import { cookies } from "next/headers";

export async function middleware(request) {
  const { pathname } = request.nextUrl;
  const cookieStore = await cookies();
  const cookieString = cookieStore.toString();
  // Retrieve the token from cookies or headers
  const token = request.cookies.get("token")?.value;
  console.log(token);

  const backend_url = process.env.API_URL || "http://127.0.0.1:8000"; // Fallback in case API_URL is undefined

  const restricted = ["/profile"];
  const not_restricted = ["/login", "/sign-up"];
  // const restricted = ["/profile"];
  // Define routes that require authentication
  // const requiresAuth = pathname.startsWith(restricted);
  const requiresAuth = restricted;

  // // Redirect to login if no token is found for protected routes
  // if (!token && requiresAuth) {
  //   return NextResponse.redirect(new URL("/login", request.url));
  // }

  // Fix for PayU redirects
  if (pathname === "/payment-process") {
    const reqHeaders = new Headers(request.headers);
    reqHeaders.set("x-forwarded-host", process.env.DOMAIN);
    return NextResponse.next({ request: { headers: reqHeaders } });
  }

  // Validate the token if it exists and the route requires authentication
  const response = await fetch(`${backend_url}/profile/`, {
    method: "GET",
    credentials: "include",
    headers: {
      "Content-Type": "application/json",
      Cookie: cookieString,
    },
  });
  const data = await response.text();

  try {
    if (pathname.startsWith("/checkout")) {
      let checkout_source = request.cookies.get("checkout_source");
      console.log(checkout_source);
      if (checkout_source === undefined) {
        return NextResponse.redirect(new URL("/", request.url));
      }
    }
    if (pathname.startsWith("/payment")) {
      let payment_token = request.cookies.get("payment_token");
      if (
        !payment_token ||
        payment_token.value !== process.env.PAYMENT_SECRET
      ) {
        return NextResponse.redirect(new URL("/", request.url));
      }
    }
  } catch (error) {
    console.error("Error validating token:", error.message, error);
    return NextResponse.redirect(new URL("/login", request.url));
  }
  // Proceed to the requested page if all checks pass
  return NextResponse.next();
}

// Configuration for paths to match
export const config = {
  matcher: ["/profile/:path*"], // Match all profile routes
  // matcher: ["/profile/:path*"], // Match all profile routes
};
