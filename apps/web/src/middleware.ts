import { auth } from "@/lib/auth";

export default auth((req) => {
  const isAuthenticated = !!req.auth?.user;
  const path = req.nextUrl.pathname;

  const needsAuth =
    path.startsWith("/dashboard") || path.startsWith("/pricing");

  if (needsAuth && !isAuthenticated) {
    const loginUrl = new URL("/login", req.nextUrl.origin);
    loginUrl.searchParams.set("callbackUrl", path);
    return Response.redirect(loginUrl);
  }
});

export const config = {
  matcher: ["/dashboard/:path*", "/pricing/:path*"],
};
