"use client";

import { useState, useCallback } from "react";
import { useRouter } from "next/navigation";
import { useSession } from "next-auth/react";
import { ArrowRight, Search } from "lucide-react";
import { ApiError, apiFetch } from "@/lib/api";
import type { LookupResponse } from "@/types/api";

export default function AddressSearch() {
  const router = useRouter();
  const { data: session } = useSession();
  const [address, setAddress] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const handleSearch = useCallback(async () => {
    if (!address.trim()) return;
    setLoading(true);
    setError(null);

    try {
      const result = await apiFetch<LookupResponse>(
        `/api/v1/lookup?address=${encodeURIComponent(address)}`,
        { token: session?.accessToken },
      );

      if (result.address_id) {
        router.push(`/report/${result.address_id}`);
        return;
      }

      setError("Lookup did not return a report. Please try again.");
    } catch (err) {
      if (err instanceof ApiError && err.status === 422) {
        setError(
          "We couldn't find that address. Try a full street address in the U.S.",
        );
        return;
      }

      setError(
        err instanceof Error
          ? err.message
          : "Something went wrong. Please try again.",
      );
    } finally {
      setLoading(false);
    }
  }, [address, router, session]);

  return (
    <div className="space-y-3">
      <form
        className="flex flex-col sm:flex-row gap-2 p-2 rounded-2xl bg-card border border-border shadow-[0_8px_30px_-12px] shadow-primary/15"
        onSubmit={(e) => {
          e.preventDefault();
          void handleSearch();
        }}
      >
        <div className="flex items-center gap-3 flex-1 px-4">
          <Search
            className="w-5 h-5 text-muted-foreground shrink-0"
            aria-hidden="true"
          />
          <input
            type="text"
            value={address}
            onChange={(e) => setAddress(e.target.value)}
            placeholder="Enter any U.S. address…"
            className="flex-1 bg-transparent py-3 text-sm placeholder:text-muted-foreground/60 focus:outline-none min-w-0"
            aria-label="U.S. address"
          />
        </div>
        <button
          type="submit"
          disabled={loading || !address.trim()}
          className="inline-flex items-center justify-center gap-2 rounded-xl bg-primary text-primary-foreground px-6 py-3 text-sm font-semibold hover:opacity-90 transition-opacity shrink-0 disabled:opacity-50 disabled:cursor-not-allowed"
        >
          {loading ? "Searching…" : "Score it"}
          {!loading && <ArrowRight className="w-4 h-4" aria-hidden="true" />}
        </button>
      </form>
      {error ? (
        <p className="text-sm text-destructive" role="alert">
          {error}
        </p>
      ) : null}
    </div>
  );
}
