"use client";

import { useEffect, useRef } from "react";
import mapboxgl from "mapbox-gl";
import "mapbox-gl/dist/mapbox-gl.css";

interface MapViewProps {
  lat: number;
  lng: number;
  address?: string;
}

export default function MapView({ lat, lng, address }: MapViewProps) {
  const containerRef = useRef<HTMLDivElement>(null);
  const mapRef = useRef<mapboxgl.Map | null>(null);
  const mapboxToken = process.env.NEXT_PUBLIC_MAPBOX_TOKEN;

  useEffect(() => {
    const token = mapboxToken;
    if (!containerRef.current || !token) return;

    mapboxgl.accessToken = token;

    const map = new mapboxgl.Map({
      container: containerRef.current,
      style: "mapbox://styles/mapbox/streets-v12",
      center: [lng, lat],
      zoom: 14,
    });

    mapRef.current = map;

    const marker = new mapboxgl.Marker({ color: "#2dd4bf" })
      .setLngLat([lng, lat])
      .addTo(map);

    if (address) {
      marker.setPopup(
        new mapboxgl.Popup({ offset: 24 }).setText(address),
      );
    }

    map.addControl(new mapboxgl.NavigationControl(), "top-right");

    return () => {
      map.remove();
      mapRef.current = null;
    };
  }, [lat, lng, address, mapboxToken]);

  if (!mapboxToken) {
    return (
      <div className="h-[400px] rounded-2xl border border-border bg-muted flex items-center justify-center text-sm text-muted-foreground">
        Map unavailable — set NEXT_PUBLIC_MAPBOX_TOKEN in your environment.
      </div>
    );
  }

  return (
    <div
      ref={containerRef}
      className="h-[400px] w-full rounded-2xl border border-border overflow-hidden shadow-lg shadow-primary/10"
      aria-label={address ? `Map showing ${address}` : "Neighborhood map"}
    />
  );
}
