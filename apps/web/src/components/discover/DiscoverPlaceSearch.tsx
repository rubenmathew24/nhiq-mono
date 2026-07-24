"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import { useRouter } from "next/navigation";
import { ArrowRight, Search } from "lucide-react";
import {
  buildDiscoverMapHref,
  paddedBBoxFromCenter,
} from "@/types/discover";

type PlaceSuggestion = {
  id: string;
  place_name: string;
  bbox: [number, number, number, number] | null;
  center: [number, number] | null;
};

const MIN_CHARS = 3;
const DEBOUNCE_MS = 250;

export default function DiscoverPlaceSearch() {
  const router = useRouter();
  const [query, setQuery] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [suggestions, setSuggestions] = useState<PlaceSuggestion[]>([]);
  const [open, setOpen] = useState(false);
  const [activeIndex, setActiveIndex] = useState(-1);
  const debounceRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  const wrapRef = useRef<HTMLDivElement>(null);

  const fetchSuggestions = useCallback(async (text: string) => {
    const token = process.env.NEXT_PUBLIC_MAPBOX_TOKEN?.trim();
    if (!token || text.trim().length < MIN_CHARS) {
      setSuggestions([]);
      return;
    }
    try {
      const url = new URL(
        `https://api.mapbox.com/geocoding/v5/mapbox.places/${encodeURIComponent(text.trim())}.json`,
      );
      url.searchParams.set("access_token", token);
      url.searchParams.set("country", "US");
      url.searchParams.set("types", "place,locality");
      url.searchParams.set("limit", "5");
      const res = await fetch(url.toString());
      if (!res.ok) {
        setSuggestions([]);
        return;
      }
      const data = (await res.json()) as {
        features?: Array<{
          id: string;
          place_name: string;
          bbox?: number[];
          center?: number[];
        }>;
      };
      setSuggestions(
        (data.features ?? []).map((f) => ({
          id: f.id,
          place_name: f.place_name,
          bbox:
            Array.isArray(f.bbox) && f.bbox.length === 4
              ? [f.bbox[0], f.bbox[1], f.bbox[2], f.bbox[3]]
              : null,
          center:
            Array.isArray(f.center) && f.center.length >= 2
              ? [f.center[0], f.center[1]]
              : null,
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
      void fetchSuggestions(query);
    }, DEBOUNCE_MS);
    return () => {
      if (debounceRef.current) clearTimeout(debounceRef.current);
    };
  }, [query, fetchSuggestions]);

  useEffect(() => {
    const onDoc = (e: MouseEvent) => {
      if (!wrapRef.current?.contains(e.target as Node)) {
        setOpen(false);
      }
    };
    document.addEventListener("mousedown", onDoc);
    return () => document.removeEventListener("mousedown", onDoc);
  }, []);

  const goToPlace = useCallback(
    (place: PlaceSuggestion) => {
      setError(null);
      setOpen(false);
      let bbox = place.bbox
        ? {
            min_lng: place.bbox[0],
            min_lat: place.bbox[1],
            max_lng: place.bbox[2],
            max_lat: place.bbox[3],
          }
        : null;
      if (!bbox && place.center) {
        bbox = paddedBBoxFromCenter(place.center[0], place.center[1]);
      }
      if (!bbox) {
        setError(
          "We couldn't determine a map area for that place. Try another city.",
        );
        return;
      }
      router.push(
        buildDiscoverMapHref({
          place: place.place_name,
          ...bbox,
        }),
      );
    },
    [router],
  );

  const onSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (activeIndex >= 0 && suggestions[activeIndex]) {
      goToPlace(suggestions[activeIndex]);
      return;
    }
    if (suggestions[0]) {
      goToPlace(suggestions[0]);
      return;
    }
    setError(
      query.trim().length < MIN_CHARS
        ? "Type at least 3 characters to search for a U.S. city."
        : "No matching U.S. cities found. Try a different spelling.",
    );
  };

  const tokenMissing = !process.env.NEXT_PUBLIC_MAPBOX_TOKEN?.trim();

  return (
    <div ref={wrapRef} className="w-full max-w-xl relative">
      <form onSubmit={onSubmit} className="flex gap-2">
        <label className="sr-only" htmlFor="discover-place">
          U.S. city or place
        </label>
        <div className="relative flex-1">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground" />
          <input
            id="discover-place"
            type="text"
            value={query}
            onChange={(e) => {
              setQuery(e.target.value);
              setError(null);
            }}
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
              }
            }}
            placeholder="Search a U.S. city (e.g. Boston, MA)"
            autoComplete="off"
            className="w-full rounded-xl border border-border bg-background pl-10 pr-3 py-3 text-sm outline-none focus:ring-2 focus:ring-mint/40"
          />
          {open && suggestions.length > 0 && (
            <ul
              role="listbox"
              className="absolute z-20 mt-1 w-full rounded-xl border border-border bg-background shadow-lg overflow-hidden"
            >
              {suggestions.map((s, i) => (
                <li key={s.id}>
                  <button
                    type="button"
                    role="option"
                    aria-selected={i === activeIndex}
                    className={`w-full text-left px-4 py-2.5 text-sm hover:bg-muted ${
                      i === activeIndex ? "bg-muted" : ""
                    }`}
                    onMouseDown={(e) => e.preventDefault()}
                    onClick={() => goToPlace(s)}
                  >
                    {s.place_name}
                  </button>
                </li>
              ))}
            </ul>
          )}
        </div>
        <button
          type="submit"
          className="inline-flex items-center gap-2 rounded-xl bg-mint px-4 py-3 text-sm font-semibold text-background hover:opacity-90"
        >
          Explore
          <ArrowRight className="h-4 w-4" />
        </button>
      </form>
      {tokenMissing && (
        <p className="mt-3 text-sm text-muted-foreground">
          Map search needs NEXT_PUBLIC_MAPBOX_TOKEN in your environment.
        </p>
      )}
      {error && (
        <p className="mt-3 text-sm text-red-500" role="alert">
          {error}
        </p>
      )}
    </div>
  );
}
