"use client";

import { Suspense, useEffect, useState } from "react";
import Link from "next/link";
import { useSearchParams } from "next/navigation";
import DiscoverMap from "@/components/discover/DiscoverMap";
import DiscoverLegend from "@/components/discover/DiscoverLegend";
import DiscoverCoverageBanner from "@/components/discover/DiscoverCoverageBanner";
import DiscoverCitySummary from "@/components/discover/DiscoverCitySummary";
import { ApiError, apiFetch } from "@/lib/api";
import {
  discoverTractsResponseSchema,
  type DiscoverBBox,
  type DiscoverTractsResponse,
} from "@/types/discover";

function parseBBox(params: URLSearchParams): DiscoverBBox | null {
  const min_lng = Number(params.get("min_lng"));
  const min_lat = Number(params.get("min_lat"));
  const max_lng = Number(params.get("max_lng"));
  const max_lat = Number(params.get("max_lat"));
  if (![min_lng, min_lat, max_lng, max_lat].every(Number.isFinite)) {
    return null;
  }
  if (min_lng >= max_lng || min_lat >= max_lat) return null;
  return { min_lng, min_lat, max_lng, max_lat };
}

function bboxFetchKey(bbox: DiscoverBBox, place: string): string {
  return [
    place,
    bbox.min_lng,
    bbox.min_lat,
    bbox.max_lng,
    bbox.max_lat,
  ].join("|");
}

function DiscoverMapInner() {
  const searchParams = useSearchParams();
  const place = searchParams.get("place")?.trim() || "Selected place";
  const bbox = parseBBox(searchParams);

  if (!bbox) {
    return (
      <div className="space-y-4">
        <h1 className="font-display text-3xl font-bold">Discover map</h1>
        <p className="text-muted-foreground">
          This map link is missing a valid place area. Search again from
          Discover.
        </p>
        <Link href="/discover" className="text-mint font-semibold underline">
          Back to Discover
        </Link>
      </div>
    );
  }

  // Remount on place/bbox change so load/error/focus reset without sync setState in effects.
  return (
    <DiscoverMapLoader
      key={bboxFetchKey(bbox, place)}
      bbox={bbox}
      place={place}
    />
  );
}

function DiscoverMapLoader({
  bbox,
  place,
}: {
  bbox: DiscoverBBox;
  place: string;
}) {
  const [tracts, setTracts] = useState<DiscoverTractsResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [focusedGeoid, setFocusedGeoid] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;

    const qs = new URLSearchParams({
      min_lng: String(bbox.min_lng),
      min_lat: String(bbox.min_lat),
      max_lng: String(bbox.max_lng),
      max_lat: String(bbox.max_lat),
      place_name: place,
    });

    void (async () => {
      try {
        const raw = await apiFetch<unknown>(
          `/api/v1/discover/tracts?${qs.toString()}`,
        );
        const parsed = discoverTractsResponseSchema.safeParse(raw);
        if (!parsed.success) {
          if (!cancelled) {
            setError("We received unexpected map data. Please try again.");
          }
          return;
        }
        if (!cancelled) setTracts(parsed.data);
      } catch (err) {
        if (cancelled) return;
        if (err instanceof ApiError) {
          setError(err.message);
        } else {
          setError("Something went wrong. Please try again.");
        }
      } finally {
        if (!cancelled) setLoading(false);
      }
    })();

    return () => {
      cancelled = true;
    };
  }, [bbox, place]);

  const scores =
    tracts?.features.map((f) => f.properties.overall_score) ?? [];

  return (
    <div className="space-y-6">
      <div className="flex flex-col md:flex-row md:items-end md:justify-between gap-4">
        <div className="space-y-2">
          <p className="text-sm font-semibold uppercase tracking-wide text-mint">
            Discover
          </p>
          <h1 className="font-display text-3xl md:text-4xl font-bold tracking-tight">
            {place}
          </h1>
          <p className="text-sm text-muted-foreground">
            Census tracts colored by relative overall neighborhood score.
            Click a tract for details.
          </p>
        </div>
        <Link
          href="/discover"
          className="text-sm font-semibold text-mint hover:underline shrink-0"
        >
          Search another place
        </Link>
      </div>

      {error && (
        <div
          className="rounded-xl border border-red-500/30 bg-background px-4 py-3 text-sm"
          role="alert"
        >
          {error}
        </div>
      )}

      {loading && (
        <p className="text-sm text-muted-foreground">
          Loading neighborhood overlay…
        </p>
      )}

      {tracts && (
        <DiscoverCoverageBanner
          scoredCount={tracts.meta.scored_count}
          unscoredCount={tracts.meta.unscored_count}
          truncated={tracts.meta.truncated}
        />
      )}

      <div className="relative">
        <DiscoverMap
          bbox={bbox}
          placeName={place}
          tracts={tracts}
          focusedGeoid={focusedGeoid}
        />
        <div className="absolute left-3 bottom-3 z-10 pointer-events-none">
          <div className="pointer-events-auto">
            <DiscoverLegend scores={scores} />
          </div>
        </div>
      </div>

      {tracts?.summary && (
        <DiscoverCitySummary
          summary={tracts.summary}
          focusedGeoid={focusedGeoid}
          onFocusGeoid={setFocusedGeoid}
        />
      )}
    </div>
  );
}

export default function DiscoverMapClient() {
  return (
    <Suspense
      fallback={
        <p className="text-muted-foreground">Loading Discover map…</p>
      }
    >
      <DiscoverMapInner />
    </Suspense>
  );
}
