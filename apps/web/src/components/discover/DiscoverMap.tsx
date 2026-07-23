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
};

const SOURCE_ID = "discover-tracts";
const FILL_ID = "discover-tracts-fill";
const LINE_ID = "discover-tracts-line";

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

export default function DiscoverMap({ bbox, placeName, tracts }: Props) {
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

    // Slight padding so maxBounds doesn't feel stuck on the edges.
    const pad = 0.02;
    const spanLng = Math.max(bbox.max_lng - bbox.min_lng, 0.01);
    const spanLat = Math.max(bbox.max_lat - bbox.min_lat, 0.01);
    const maxBounds: mapboxgl.LngLatBoundsLike = [
      [bbox.min_lng - spanLng * pad, bbox.min_lat - spanLat * pad],
      [bbox.max_lng + spanLng * pad, bbox.max_lat + spanLat * pad],
    ];

    const map = new mapboxgl.Map({
      container: containerRef.current,
      style: "mapbox://styles/mapbox/light-v11",
      bounds,
      fitBoundsOptions: { padding: 40 },
      maxBounds,
      minZoom: 8,
    });

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
