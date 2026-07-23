/** Relative choropleth colors for Discover (null = unscored gray). */

export const UNSCORED_TRACT_COLOR = "#9ca3af";

/** Low → mid → high ramp (red → amber → teal). */
const RAMP = [
  { t: 0, color: [239, 68, 68] as const }, // red-500
  { t: 0.5, color: [245, 158, 11] as const }, // amber-500
  { t: 1, color: [45, 212, 191] as const }, // teal-400
];

function lerp(a: number, b: number, t: number): number {
  return Math.round(a + (b - a) * t);
}

function mix(
  c0: readonly [number, number, number],
  c1: readonly [number, number, number],
  t: number,
): string {
  return `rgb(${lerp(c0[0], c1[0], t)}, ${lerp(c0[1], c1[1], t)}, ${lerp(c0[2], c1[2], t)})`;
}

export function scoreRange(
  scores: Array<number | null | undefined>,
): { min: number; max: number } | null {
  const vals = scores.filter((s): s is number => typeof s === "number" && Number.isFinite(s));
  if (vals.length === 0) return null;
  return { min: Math.min(...vals), max: Math.max(...vals) };
}

/** Map a score onto the relative ramp for the current view. */
export function relativeScoreColor(
  score: number | null | undefined,
  min: number,
  max: number,
): string {
  if (score == null || !Number.isFinite(score)) {
    return UNSCORED_TRACT_COLOR;
  }
  if (min === max) {
    return mix(RAMP[1].color, RAMP[1].color, 0);
  }
  const t = Math.min(1, Math.max(0, (score - min) / (max - min)));
  if (t <= 0.5) {
    return mix(RAMP[0].color, RAMP[1].color, t / 0.5);
  }
  return mix(RAMP[1].color, RAMP[2].color, (t - 0.5) / 0.5);
}

/** Build a Mapbox match expression: ["match", ["get","geoid"], geoid, color, ..., gray] */
export function buildFillColorExpression(
  features: Array<{
    properties: { geoid: string; overall_score: number | null };
  }>,
): unknown[] {
  const range = scoreRange(features.map((f) => f.properties.overall_score));
  const expr: unknown[] = ["match", ["get", "geoid"]];
  for (const f of features) {
    const color = range
      ? relativeScoreColor(f.properties.overall_score, range.min, range.max)
      : UNSCORED_TRACT_COLOR;
    expr.push(f.properties.geoid, color);
  }
  expr.push(UNSCORED_TRACT_COLOR);
  return expr;
}
