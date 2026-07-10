import NextAuth from "next-auth";
import Credentials from "next-auth/providers/credentials";
import { apiFetch } from "./api";
import type { UserTier } from "@/types/api";
import type { TokenResponse } from "@/types/api";

export const { handlers, signIn, signOut, auth } = NextAuth({
  // Auth.js v5 prefers AUTH_SECRET; NEXTAUTH_SECRET kept for compatibility.
  secret: process.env.AUTH_SECRET ?? process.env.NEXTAUTH_SECRET,
  providers: [
    Credentials({
      credentials: {
        email: { label: "Email", type: "email" },
        password: { label: "Password", type: "password" },
      },
      async authorize(credentials) {
        try {
          const response = await apiFetch<TokenResponse>("/api/v1/auth/login", {
            method: "POST",
            body: JSON.stringify({
              email: credentials?.email,
              password: credentials?.password,
            }),
          });
          return {
            id: response.user.id,
            email: response.user.email,
            name: response.user.full_name,
            accessToken: response.access_token,
            tier: response.user.tier,
          };
        } catch {
          return null;
        }
      },
    }),
  ],
  callbacks: {
    async jwt({ token, user }) {
      if (user) {
        token.accessToken = user.accessToken;
        token.tier = user.tier;
      }
      return token;
    },
    async session({ session, token }) {
      const accessToken =
        typeof token.accessToken === "string" ? token.accessToken : undefined;
      const tier =
        typeof token.tier === "string" ? (token.tier as UserTier) : undefined;
      session.accessToken = accessToken;
      session.tier = tier;
      if (session.user) {
        session.user.tier = tier;
      }
      return session;
    },
  },
  pages: {
    signIn: "/login",
  },
});
