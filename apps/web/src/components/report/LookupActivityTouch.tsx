"use client";

import { useEffect, useRef } from "react";
import { useSession } from "next-auth/react";
import { apiFetch } from "@/lib/api";

/** Bumps dashboard recency when a signed-in user opens a saved report. */
export default function LookupActivityTouch({
  addressId,
}: {
  addressId: string;
}) {
  const { data: session, status } = useSession();
  const sent = useRef(false);

  useEffect(() => {
    if (status !== "authenticated" || !session?.accessToken || sent.current) {
      return;
    }
    sent.current = true;
    void apiFetch(`/api/v1/users/me/lookups/${addressId}/touch`, {
      method: "POST",
      token: session.accessToken,
    }).catch(() => {
      // Not saved for this user — ignore
      sent.current = false;
    });
  }, [addressId, session?.accessToken, status]);

  return null;
}
