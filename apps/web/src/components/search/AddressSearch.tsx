"use client";

import { useState, useCallback, useEffect, useRef } from "react";
import { useRouter } from "next/navigation";
import { useSession } from "next-auth/react";
import { ArrowRight, Search } from "lucide-react";
import { ApiError, apiFetch } from "@/lib/api";
import type { LookupResponse } from "@/types/api";

type PlaceSuggestion = {
  id: string;
  place_name: string;
};

const MIN_CHARS = 3;
const DEBOUNCE_MS = 250;

export default function AddressSearch() {
  const router = useRouter();
  const { data: session } = useSession();
  const [address, setAddress] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [suggestions, setSuggestions] = useState<PlaceSuggestion[]>([]);
  const [open, setOpen] = useState(false);
  const [activeIndex, setActiveIndex] = useState(-1);
  const debounceRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  const wrapRef = useRef<HTMLDivElement>(null);

  const fetchSuggestions = useCallback(async (query: string) => {
    const token = process.env.NEXT_PUBLIC_MAPBOX_TOKEN?.trim();
    if (!token || query.trim().length < MIN_CHARS) {
      setSuggestions([]);
      return;
    }
    try {
      const url = new URL(
        `https://api.mapbox.com/geocoding/v5/mapbox.places/${encodeURIComponent(query.trim())}.json`,
      );
      url.searchParams.set("access_token", token);
      url.searchParams.set("country", "US");
      url.searchParams.set("types", "address");
      url.searchParams.set("limit", "5");
      const res = await fetch(url.toString());
      if (!res.ok) {
        setSuggestions([]);
        return;
      }
      const data = (await res.json()) as {
        features?: { id: string; place_name: string }[];
      };
      setSuggestions(
        (data.features ?? []).map((f) => ({
          id: f.id,
          place_name: f.place_name,
        })),
      );
      setOpen(true);
      setActiveIndex(-1);
    } catch {
      setSuggestions([]);
    }
  }, []);

  useEffect(() => {
    if (debounceRef.current) clearTimeout(debounceRef.current);
    debounceRef.current = setTimeout(() => {
      void fetchSuggestions(address);
    }, DEBOUNCE_MS);
    return () => {
      if (debounceRef.current) clearTimeout(debounceRef.current);
    };
  }, [address, fetchSuggestions]);

  useEffect(() => {
    const onDoc = (e: MouseEvent) => {
      if (!wrapRef.current?.contains(e.target as Node)) {
        setOpen(false);
      }
    };
    document.addEventListener("mousedown", onDoc);
    return () => document.removeEventListener("mousedown", onDoc);
  }, []);

  const runLookup = useCallback(
    async (query: string) => {
      if (!query.trim()) return;
      setLoading(true);
      setError(null);
      setOpen(false);

      try {
        const result = await apiFetch<LookupResponse>(
          `/api/v1/lookup?address=${encodeURIComponent(query)}`,
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
    },
    [router, session],
  );

  const handleSearch = useCallback(async () => {
    await runLookup(address);
  }, [address, runLookup]);

  const pickSuggestion = (placeName: string) => {
    setAddress(placeName);
    setSuggestions([]);
    setOpen(false);
    void runLookup(placeName);
  };

  return (
    <div className="space-y-3" ref={wrapRef}>
      <form
        className="flex flex-col sm:flex-row gap-2 p-2 rounded-2xl bg-card border border-border shadow-[0_8px_30px_-12px] shadow-primary/15 relative"
        onSubmit={(e) => {
          e.preventDefault();
          void handleSearch();
        }}
      >
        <div className="flex items-center gap-3 flex-1 px-4 relative min-w-0">
          <Search
            className="w-5 h-5 text-muted-foreground shrink-0"
            aria-hidden="true"
          />
          <input
            type="text"
            value={address}
            onChange={(e) => setAddress(e.target.value)}
            onFocus={() => suggestions.length > 0 && setOpen(true)}
            onKeyDown={(e) => {
              if (!open || suggestions.length === 0) return;
              if (e.key === "ArrowDown") {
                e.preventDefault();
                setActiveIndex((i) => Math.min(i + 1, suggestions.length - 1));
              } else if (e.key === "ArrowUp") {
                e.preventDefault();
                setActiveIndex((i) => Math.max(i - 1, 0));
              } else if (e.key === "Escape") {
                setOpen(false);
              } else if (e.key === "Enter" && activeIndex >= 0) {
                e.preventDefault();
                pickSuggestion(suggestions[activeIndex].place_name);
              }
            }}
            placeholder="Enter any U.S. address…"
            className="flex-1 bg-transparent py-3 text-sm placeholder:text-muted-foreground/60 focus:outline-none min-w-0"
            aria-label="U.S. address"
            aria-autocomplete="list"
            aria-expanded={open}
            aria-controls="address-suggestions"
          />
          {open && suggestions.length > 0 ? (
            <ul
              id="address-suggestions"
              role="listbox"
              className="absolute left-0 right-0 top-full z-40 mt-2 overflow-hidden rounded-xl border border-border bg-card shadow-lg"
            >
              {suggestions.map((s, idx) => (
                <li key={s.id} role="option" aria-selected={idx === activeIndex}>
                  <button
                    type="button"
                    className={`w-full text-left px-4 py-2.5 text-sm hover:bg-muted/60 ${
                      idx === activeIndex ? "bg-muted/60" : ""
                    }`}
                    onMouseDown={(e) => e.preventDefault()}
                    onClick={() => pickSuggestion(s.place_name)}
                  >
                    {s.place_name}
                  </button>
                </li>
              ))}
            </ul>
          ) : null}
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
