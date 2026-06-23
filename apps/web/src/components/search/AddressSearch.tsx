"use client";

import { useState, useCallback } from "react";
import { useRouter } from "next/navigation";
import { ArrowRight, Search } from "lucide-react";
import { ApiError, apiFetch } from "@/lib/api";
import type { LookupResponse } from "@/types/api";

export default function AddressSearch() {
  const router = useRouter();
  const [address, setAddress] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const handleSearch = useCallback(async () => {
    if (!address.trim()) return;
    setLoading(true);
    setError(null);

    const lookupPath = `/api/v1/lookup?address=${encodeURIComponent(address)}`;
    // #region agent log
    fetch("http://127.0.0.1:7840/ingest/20a8000b-d31a-4591-ae7d-d359808c8413", {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        "X-Debug-Session-Id": "9a6fa9",
      },
      body: JSON.stringify({
        sessionId: "9a6fa9",
        runId: "pre-fix",
        hypothesisId: "A,D",
        location: "AddressSearch.tsx:handleSearch:start",
        message: "lookup request starting",
        data: {
          apiBase: process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000",
          lookupPath,
          addressLength: address.trim().length,
        },
        timestamp: Date.now(),
      }),
    }).catch(() => {});
    // #endregion

    try {
      const result = await apiFetch<LookupResponse>(lookupPath);

      // #region agent log
      fetch(
        "http://127.0.0.1:7840/ingest/20a8000b-d31a-4591-ae7d-d359808c8413",
        {
          method: "POST",
          headers: {
            "Content-Type": "application/json",
            "X-Debug-Session-Id": "9a6fa9",
          },
          body: JSON.stringify({
            sessionId: "9a6fa9",
            runId: "pre-fix",
            hypothesisId: "A",
            location: "AddressSearch.tsx:handleSearch:success",
            message: "lookup succeeded",
            data: {
              hasAddressId: Boolean(result.address_id),
              status: result.status,
            },
            timestamp: Date.now(),
          }),
        },
      ).catch(() => {});
      // #endregion

      if (result.address_id) {
        router.push(`/report/${result.address_id}`);
        return;
      }

      setError("Lookup did not return a report. Please try again.");
    } catch (err) {
      // #region agent log
      fetch(
        "http://127.0.0.1:7840/ingest/20a8000b-d31a-4591-ae7d-d359808c8413",
        {
          method: "POST",
          headers: {
            "Content-Type": "application/json",
            "X-Debug-Session-Id": "9a6fa9",
          },
          body: JSON.stringify({
            sessionId: "9a6fa9",
            runId: "pre-fix",
            hypothesisId: "A,B,C,D",
            location: "AddressSearch.tsx:handleSearch:error",
            message: "lookup failed",
            data: {
              isApiError: err instanceof ApiError,
              status: err instanceof ApiError ? err.status : null,
              errorMessage:
                err instanceof Error ? err.message : "unknown error",
            },
            timestamp: Date.now(),
          }),
        },
      ).catch(() => {});
      // #endregion

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
  }, [address, router]);

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
      {error && <p className="text-red-500 text-sm">{error}</p>}
    </div>
  );
}
