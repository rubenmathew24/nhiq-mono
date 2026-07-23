"use client";

import { useEffect, useRef } from "react";
import mapboxgl from "mapbox-gl";
import "mapbox-gl/dist/mapbox-gl.css";
import {
  buildFillColorExpression,
  UNSCORED_TRACT_COLOR,
} from "@/lib/discoverColors";
import { popupCopy } from "@/lib/discoverPopup";
import type { DiscoverBBox, DiscoverTractsResponse } from "@/types/discover";

type Props = {
  bbox: DiscoverBBox;
  placeName: string;
  tracts: DiscoverTractsResponse | null;
  focusedGeoid?: string | null;
};

const SOURCE_ID = "discover-tracts";
const FILL_ID = "discover-tracts-fill";
const LINE_ID = "discover-tracts-line";
/** Padding for city framing — minZoom is locked to this fit so scroll/UI match un-focus. */
const CITY_FIT_PADDING = 40;

function cityBounds(bbox: DiscoverBBox): mapboxgl.LngLatBoundsLike {
  return [
    [bbox.min_lng, bbox.min_lat],
    [bbox.max_lng, bbox.max_lat],
  ];
}

/**
 * Fit place bbox (with padding), then lock minZoom + maxBounds to that framing.
 * Place-only maxBounds is tighter than a padded fitBounds view, which blocked
 * scroll-zoom from reaching the same floor as un-focus / nav −.
 */
function fitCityAndLockMinZoom(
  map: mapboxgl.Map,
  bbox: DiscoverBBox,
  options?: { duration?: number; onDone?: () => void },
) {
  const duration = options?.duration ?? 0;
  const applyLock = () => {
    const z = map.getZoom();
    map.setMinZoom(z);
    const b = map.getBounds();
    const padX = Math.max((b.getEast() - b.getWest()) * 0.02, 0.001);
    const padY = Math.max((b.getNorth() - b.getSouth()) * 0.02, 0.001);
    map.setMaxBounds([
      [b.getWest() - padX, b.getSouth() - padY],
      [b.getEast() + padX, b.getNorth() + padY],
    ]);
    options?.onDone?.();
  };
  if (duration > 0) {
    map.once("moveend", applyLock);
  }
  map.fitBounds(cityBounds(bbox), {
    padding: CITY_FIT_PADDING,
    duration,
    maxZoom: 14,
  });
  if (duration === 0) {
    applyLock();
  }
}

function popupHtml(geoid: string, score: number | null): string {
  const summary = popupCopy(geoid, score);
  if (score == null) {
    return `<div style="font-family:system-ui,sans-serif;padding:2px 4px;min-width:140px">
      <div style="color:#6b7280">Score unavailable</div>
      <div style="margin-top:6px;font-size:0.7rem;color:#9ca3af">Tract ${geoid}</div>
      <span style="display:none">${summary}</span>
    </div>`;
  }
  return `<div style="font-family:system-ui,sans-serif;padding:2px 4px;min-width:140px">
    <div style="font-size:1.25rem;font-weight:700">${score.toFixed(1)}</div>
    <div style="color:#6b7280;font-size:0.75rem">Overall neighborhood score</div>
    <div style="margin-top:6px;font-size:0.7rem;color:#9ca3af">Tract ${geoid}</div>
    <span style="display:none">${summary}</span>
  </div>`;
}

/** Expand ring coordinates into a LngLatBounds. */
function boundsFromGeometry(geometry: GeoJSON.Geometry): mapboxgl.LngLatBounds | null {
  const bounds = new mapboxgl.LngLatBounds();
  let any = false;

  const extend = (coords: number[][]) => {
    for (const c of coords) {
      if (c.length >= 2) {
        bounds.extend([c[0], c[1]]);
        any = true;
      }
    }
  };

  const walk = (g: GeoJSON.Geometry) => {
    if (g.type === "Polygon") {
      for (const ring of g.coordinates) extend(ring as number[][]);
    } else if (g.type === "MultiPolygon") {
      for (const poly of g.coordinates) {
        for (const ring of poly) extend(ring as number[][]);
      }
    } else if (g.type === "GeometryCollection") {
      for (const child of g.geometries) walk(child);
    }
  };

  walk(geometry);
  return any ? bounds : null;
}

export default function DiscoverMap({
  bbox,
  placeName,
  tracts,
  focusedGeoid = null,
}: Props) {
  const containerRef = useRef<HTMLDivElement>(null);
  const mapRef = useRef<mapboxgl.Map | null>(null);
  const popupRef = useRef<mapboxgl.Popup | null>(null);
  const mapboxToken = process.env.NEXT_PUBLIC_MAPBOX_TOKEN;

  useEffect(() => {
    const token = mapboxToken?.trim();
    if (!containerRef.current || !token) return;

    mapboxgl.accessToken = token;

    const bounds = new mapboxgl.LngLatBounds(
      [bbox.min_lng, bbox.min_lat],
      [bbox.max_lng, bbox.max_lat],
    );

    // maxBounds is applied after city fit (see fitCityAndLockMinZoom) so it matches
    // the padded framing; a tight place maxBounds blocked scroll short of minZoom.
    const map = new mapboxgl.Map({
      container: containerRef.current,
      style: "mapbox://styles/mapbox/light-v11",
      bounds,
      fitBoundsOptions: { padding: CITY_FIT_PADDING },
    });

    map.scrollZoom.enable({ around: "center" });

    map.addControl(new mapboxgl.NavigationControl({ showCompass: false }), "top-right");
    mapRef.current = map;

    const popup = new mapboxgl.Popup({
      closeButton: true,
      closeOnClick: false,
      offset: 12,
      maxWidth: "240px",
    });
    popupRef.current = popup;

    const onClick = (e: mapboxgl.MapLayerMouseEvent) => {
      const feature = e.features?.[0];
      if (!feature || feature.geometry.type === "GeometryCollection") {
        popup.remove();
        return;
      }
      const props = feature.properties as {
        geoid?: string;
        overall_score?: number | string | null;
      };
      const geoid = props.geoid ?? "unknown";
      let score: number | null = null;
      if (props.overall_score != null && props.overall_score !== "") {
        const n = Number(props.overall_score);
        score = Number.isFinite(n) ? n : null;
      }
      popup.setLngLat(e.lngLat).setHTML(popupHtml(geoid, score)).addTo(map);
    };

    const onMove = () => {
      map.getCanvas().style.cursor = "pointer";
    };
    const onLeave = () => {
      map.getCanvas().style.cursor = "";
    };

    map.on("load", () => {
      fitCityAndLockMinZoom(map, bbox, { duration: 0 });
      map.addSource(SOURCE_ID, {
        type: "geojson",
        data: { type: "FeatureCollection", features: [] },
      });
      map.addLayer({
        id: FILL_ID,
        type: "fill",
        source: SOURCE_ID,
        paint: {
          "fill-color": UNSCORED_TRACT_COLOR,
          "fill-opacity": 0.55,
        },
      });
      map.addLayer({
        id: LINE_ID,
        type: "line",
        source: SOURCE_ID,
        paint: {
          "line-color": "#334155",
          "line-width": 0.8,
          "line-opacity": 0.7,
        },
      });
      map.on("click", FILL_ID, onClick);
      map.on("mouseenter", FILL_ID, onMove);
      map.on("mouseleave", FILL_ID, onLeave);
      map.on("click", (e) => {
        const hits = map.queryRenderedFeatures(e.point, { layers: [FILL_ID] });
        if (!hits.length) popup.remove();
      });
    });

    return () => {
      popup.remove();
      map.remove();
      mapRef.current = null;
      popupRef.current = null;
    };
  }, [bbox, mapboxToken]);

  useEffect(() => {
    const map = mapRef.current;
    if (!map || !tracts) return;

    const apply = () => {
      const source = map.getSource(SOURCE_ID) as mapboxgl.GeoJSONSource | undefined;
      if (!source) return;

      const fc = {
        type: "FeatureCollection" as const,
        features: tracts.features.map((f) => ({
          type: "Feature" as const,
          geometry: f.geometry as GeoJSON.Geometry,
          properties: {
            geoid: f.properties.geoid,
            overall_score: f.properties.overall_score,
            in_city_scope: f.properties.in_city_scope,
          },
        })),
      };
      source.setData(fc);

      if (map.getLayer(FILL_ID)) {
        if (tracts.features.length === 0 || tracts.meta.scored_count === 0) {
          map.setPaintProperty(FILL_ID, "fill-color", UNSCORED_TRACT_COLOR);
          map.setLayoutProperty(FILL_ID, "visibility", "none");
          map.setLayoutProperty(LINE_ID, "visibility", "none");
        } else {
          map.setLayoutProperty(FILL_ID, "visibility", "visible");
          map.setLayoutProperty(LINE_ID, "visibility", "visible");
          map.setPaintProperty(
            FILL_ID,
            "fill-color",
            buildFillColorExpression(tracts.features) as mapboxgl.ExpressionSpecification,
          );
        }
      }
    };

    if (map.isStyleLoaded()) {
      apply();
    } else {
      map.once("load", apply);
    }
  }, [tracts]);

  // Focus: dim others + gentle fit; clear restores city framing.
  useEffect(() => {
    const map = mapRef.current;
    if (!map) return;
    let cancelled = false;

    const applyFocus = () => {
      if (cancelled || !map.getLayer(FILL_ID)) return;

      // Kill any in-flight camera animation so leave→enter races don't land mid-city.
      map.stop();

      if (!focusedGeoid) {
        map.setPaintProperty(FILL_ID, "fill-opacity", 0.55);
        fitCityAndLockMinZoom(map, bbox, { duration: 600 });
        return;
      }

      map.setPaintProperty(FILL_ID, "fill-opacity", [
        "case",
        ["==", ["get", "geoid"], focusedGeoid],
        0.75,
        0.12,
      ] as mapboxgl.ExpressionSpecification);

      const feature = tracts?.features.find(
        (f) => f.properties.geoid === focusedGeoid,
      );
      if (!feature) return;
      const featureBounds = boundsFromGeometry(
        feature.geometry as GeoJSON.Geometry,
      );
      if (!featureBounds || featureBounds.isEmpty()) return;
      map.fitBounds(featureBounds, {
        padding: 56,
        duration: 650,
        maxZoom: 13,
      });
    };

    if (map.isStyleLoaded()) {
      applyFocus();
    } else {
      map.once("load", applyFocus);
    }

    return () => {
      cancelled = true;
    };
  }, [focusedGeoid, tracts, bbox]);

  if (!mapboxToken?.trim()) {
    return (
      <div className="h-[min(70vh,640px)] w-full rounded-2xl border border-border bg-muted flex items-center justify-center text-sm text-muted-foreground">
        Map unavailable — set NEXT_PUBLIC_MAPBOX_TOKEN in your environment.
      </div>
    );
  }

  return (
    <div
      ref={containerRef}
      className="h-[min(70vh,640px)] w-full rounded-2xl border border-border overflow-hidden shadow-lg shadow-primary/10"
      aria-label={`Discover map for ${placeName}`}
    />
  );
}
