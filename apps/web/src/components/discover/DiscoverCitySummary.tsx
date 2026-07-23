"use client";

import type { DiscoverSummary } from "@/types/discover";

type Props = {
  summary: DiscoverSummary | null | undefined;
  focusedGeoid: string | null;
  onFocusGeoid: (geoid: string | null) => void;
};

function formatScore(n: number | null | undefined): string {
  if (n == null || !Number.isFinite(n)) return "—";
  return n.toFixed(1);
}

export default function DiscoverCitySummary({
  summary,
  focusedGeoid,
  onFocusGeoid,
}: Props) {
  if (!summary) return null;

  const hasPair = !summary.insufficient_data && summary.highest && summary.lowest;

  return (
    <section
      className="rounded-2xl border border-border bg-card/40 px-5 py-4 space-y-4"
      aria-label="City score snapshot"
    >
      <div className="space-y-1">
        <h2 className="font-display text-lg font-semibold tracking-tight">
          City snapshot
        </h2>
        <p className="text-sm text-muted-foreground">
          Average overall{" "}
          <span className="font-semibold text-foreground">
            {formatScore(summary.average_overall)}
          </span>
          {" · "}
          {summary.scored_count} of {summary.total_count} tracts scored
          {summary.score_min != null && summary.score_max != null && (
            <>
              {" · "}range {formatScore(summary.score_min)}–
              {formatScore(summary.score_max)}
            </>
          )}
        </p>
      </div>

      {!hasPair ? (
        <p className="text-sm text-muted-foreground" role="status">
          Not enough scored neighborhoods in this city core yet to show a
          highest and lowest pair.
        </p>
      ) : (
        <ul className="space-y-2">
          <li>
            <HighlightRow
              kind="Highest"
              geoid={summary.highest!.geoid}
              label={summary.highest!.label}
              score={summary.highest!.overall_score}
              focused={focusedGeoid === summary.highest!.geoid}
              onFocusGeoid={onFocusGeoid}
            />
          </li>
          <li>
            <HighlightRow
              kind="Lowest"
              geoid={summary.lowest!.geoid}
              label={summary.lowest!.label}
              score={summary.lowest!.overall_score}
              focused={focusedGeoid === summary.lowest!.geoid}
              onFocusGeoid={onFocusGeoid}
            />
          </li>
        </ul>
      )}
    </section>
  );
}

function HighlightRow({
  kind,
  geoid,
  label,
  score,
  focused,
  onFocusGeoid,
}: {
  kind: string;
  geoid: string;
  label: string;
  score: number;
  focused: boolean;
  onFocusGeoid: (geoid: string | null) => void;
}) {
  return (
    <button
      type="button"
      className={`w-full text-left rounded-xl border px-4 py-3 transition-colors ${
        focused
          ? "border-mint bg-mint/10"
          : "border-border hover:border-mint/50 hover:bg-muted/40"
      }`}
      onClick={() => onFocusGeoid(focused ? null : geoid)}
      aria-pressed={focused}
    >
      <div className="flex items-baseline justify-between gap-3">
        <div className="min-w-0">
          <p className="text-xs font-semibold uppercase tracking-wide text-mint">
            {kind}
          </p>
          <p className="font-medium truncate">{label}</p>
          <p className="text-xs text-muted-foreground mt-0.5">GEOID {geoid}</p>
          {focused ? (
            <p className="text-xs text-mint mt-1">Focused · click to clear</p>
          ) : null}
        </div>
        <p className="text-2xl font-bold tabular-nums shrink-0">
          {formatScore(score)}
        </p>
      </div>
    </button>
  );
}
