import { z } from "zod";

export const discoverBBoxSchema = z.object({
  min_lng: z.number(),
  min_lat: z.number(),
  max_lng: z.number(),
  max_lat: z.number(),
});

export const discoverTractHighlightSchema = z.object({
  geoid: z.string(),
  overall_score: z.number(),
  label: z.string(),
});

export const discoverSummarySchema = z.object({
  scope_mode: z.enum(["inner_bbox", "place_polygon"]),
  average_overall: z.number().nullable(),
  score_min: z.number().nullable(),
  score_max: z.number().nullable(),
  scored_count: z.number(),
  total_count: z.number(),
  highest: discoverTractHighlightSchema.nullable(),
  lowest: discoverTractHighlightSchema.nullable(),
  insufficient_data: z.boolean(),
});

export const discoverFeatureSchema = z.object({
  type: z.literal("Feature"),
  geometry: z.record(z.string(), z.unknown()),
  properties: z.object({
    geoid: z.string(),
    overall_score: z.number().nullable(),
    in_city_scope: z.boolean(),
  }),
});

export const discoverTractsResponseSchema = z.object({
  place_name: z.string().nullable().optional(),
  bbox: discoverBBoxSchema,
  type: z.literal("FeatureCollection"),
  features: z.array(discoverFeatureSchema),
  meta: z.object({
    scored_count: z.number(),
    unscored_count: z.number(),
    truncated: z.boolean(),
    score_min: z.number().nullable().optional(),
    score_max: z.number().nullable().optional(),
    data_vintage: z.string(),
  }),
  summary: discoverSummarySchema,
});

export type DiscoverBBox = z.infer<typeof discoverBBoxSchema>;
export type DiscoverSummary = z.infer<typeof discoverSummarySchema>;
export type DiscoverTractHighlight = z.infer<typeof discoverTractHighlightSchema>;
export type DiscoverTractsResponse = z.infer<typeof discoverTractsResponseSchema>;

export function buildDiscoverMapHref(input: {
  place: string;
  min_lng: number;
  min_lat: number;
  max_lng: number;
  max_lat: number;
}): string {
  const params = new URLSearchParams({
    place: input.place,
    min_lng: String(input.min_lng),
    min_lat: String(input.min_lat),
    max_lng: String(input.max_lng),
    max_lat: String(input.max_lat),
  });
  return `/discover/map?${params.toString()}`;
}

/** Fallback ~±0.15° box when Mapbox omits bbox. */
export function paddedBBoxFromCenter(
  lng: number,
  lat: number,
  padDeg = 0.15,
): DiscoverBBox {
  return {
    min_lng: lng - padDeg,
    min_lat: lat - padDeg,
    max_lng: lng + padDeg,
    max_lat: lat + padDeg,
  };
}
