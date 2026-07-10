import type { DefaultSession } from "next-auth";
import type { UserTier } from "@/types/api";

declare module "next-auth" {
  interface Session {
    accessToken?: string;
    tier?: UserTier;
    user: DefaultSession["user"] & {
      tier?: UserTier;
    };
  }

  interface User {
    accessToken?: string;
    tier?: UserTier;
  }
}

declare module "next-auth/jwt" {
  interface JWT {
    accessToken?: string;
    tier?: UserTier;
  }
}
