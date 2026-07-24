"use client";

import {
  relativeScoreColor,
  scoreRange,
  UNSCORED_TRACT_COLOR,
} from "@/lib/discoverColors";

type Props = {
  scores: Array<number | null>;
};

export default function DiscoverLegend({ scores }: Props) {
  const range = scoreRange(scores);
  if (!range) {
    return (
      <div className="rounded-xl border border-border bg-background/90 backdrop-blur px-3 py-2 text-xs text-muted-foreground shadow">
        Colors show relative overall scores for neighborhoods on this map.
        <span className="ml-2 inline-flex items-center gap-1">
          <span
            className="inline-block h-2.5 w-2.5 rounded-sm"
            style={{ background: UNSCORED_TRACT_COLOR }}
          />
          No score
        </span>
      </div>
    );
  }

  const swatches = [0, 0.25, 0.5, 0.75, 1].map((t) => {
    const score = range.min + t * (range.max - range.min);
    return relativeScoreColor(score, range.min, range.max);
  });

  return (
    <div className="rounded-xl border border-border bg-background/90 backdrop-blur px-3 py-2 text-xs shadow space-y-1.5 max-w-xs">
      <p className="font-medium text-foreground">
        Relative overall score (this view)
      </p>
      <div className="flex h-2.5 overflow-hidden rounded-full">
        {swatches.map((c, i) => (
          <span key={i} className="flex-1" style={{ background: c }} />
        ))}
      </div>
      <div className="flex justify-between text-muted-foreground">
        <span>{range.min.toFixed(0)} (lower here)</span>
        <span>{range.max.toFixed(0)} (higher here)</span>
      </div>
      <p className="text-muted-foreground flex items-center gap-1.5">
        <span
          className="inline-block h-2.5 w-2.5 rounded-sm"
          style={{ background: UNSCORED_TRACT_COLOR }}
        />
        Gray = score unavailable
      </p>
    </div>
  );
}
