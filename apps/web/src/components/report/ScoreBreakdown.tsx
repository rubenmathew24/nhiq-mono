"use client";

import { useId, useState } from "react";
import ScoreBar from "@/components/ui/ScoreBar";
import { cn, scoreTextClass } from "@/lib/utils";
import type { NeighborhoodReport, ScoreDimension, SubScore } from "@/types/api";

interface ScoreBreakdownProps {
  report: NeighborhoodReport;
}

const DIMENSIONS: { key: keyof NeighborhoodReport; title: string }[] = [
  { key: "healthcare", title: "Healthcare" },
  { key: "safety", title: "Safety" },
  { key: "environment", title: "Environment" },
  { key: "education", title: "Schools" },
  { key: "economic", title: "Economy" },
];

function SubScoreRow({ sub }: { sub: SubScore }) {
  const muted = sub.available === false;
  return (
    <div className={cn("space-y-1", muted && "opacity-60")}>
      <div className="flex items-center justify-between text-[11px]">
        <span className="text-muted-foreground">
          {sub.label}
          {muted ? " · limited data" : ""}
        </span>
        <span
          className={cn(
            "font-display font-medium tabular-nums",
            muted ? "text-muted-foreground" : scoreTextClass(sub.score),
          )}
        >
          {muted ? "—" : Math.round(sub.score)}
        </span>
      </div>
      {!muted && <ScoreBar score={sub.score} className="h-1.5" />}
    </div>
  );
}

function DimensionRow({
  title,
  dimension,
}: {
  title: string;
  dimension: ScoreDimension;
}) {
  const [open, setOpen] = useState(false);
  const panelId = useId();
  const subs = dimension.sub_scores ?? [];
  const factors = dimension.factors ?? [];

  return (
    <div className="border-b border-border/60 last:border-0 pb-4 last:pb-0">
      <button
        type="button"
        className="w-full text-left group"
        aria-expanded={open}
        aria-controls={panelId}
        aria-label={`${open ? "Collapse" : "Expand"} ${title} details`}
        onClick={() => setOpen((v) => !v)}
      >
        <div className="flex items-center justify-between text-xs mb-1 gap-2">
          <span className="text-foreground/70 font-medium flex items-center gap-1.5">
            {title}
            <span
              className={cn(
                "inline-flex text-muted-foreground transition-transform text-[10px]",
                open && "rotate-90",
              )}
              aria-hidden
            >
              ▸
            </span>
            <span className="text-[10px] font-normal text-muted-foreground group-hover:text-foreground/60">
              View details
            </span>
          </span>
          <span
            className={cn(
              "font-display font-semibold tabular-nums",
              scoreTextClass(dimension.score),
            )}
          >
            {Math.round(dimension.score)}
          </span>
        </div>
        <ScoreBar score={dimension.score} />
      </button>

      {subs.length > 0 && (
        <div className="mt-3 space-y-2 pl-0.5">
          {subs.map((s) => (
            <SubScoreRow key={s.id} sub={s} />
          ))}
        </div>
      )}

      <p className="mt-2 text-xs text-muted-foreground leading-relaxed">
        {dimension.summary}
      </p>

      {open && (
        <div
          id={panelId}
          className="mt-3 rounded-xl bg-muted/40 border border-border/50 px-3 py-2.5 space-y-2"
        >
          {factors.length === 0 ? (
            <p className="text-xs text-muted-foreground">
              Detailed stats are not available for this category yet.
            </p>
          ) : (
            factors.map((f) => (
              <div
                key={`${f.name}-${f.value}`}
                className="flex justify-between gap-3 text-xs"
              >
                <span className="text-muted-foreground shrink-0">{f.name}</span>
                <span
                  className={cn(
                    "text-right font-medium",
                    f.impact === "positive" && "text-emerald-700 dark:text-emerald-400",
                    f.impact === "negative" && "text-amber-800 dark:text-amber-400",
                    f.impact === "neutral" && "text-foreground/80",
                  )}
                >
                  {f.value}
                </span>
              </div>
            ))
          )}
        </div>
      )}
    </div>
  );
}

export default function ScoreBreakdown({ report }: ScoreBreakdownProps) {
  return (
    <div className="rounded-2xl bg-card border border-border p-6 space-y-5">
      <h2 className="text-sm font-semibold uppercase tracking-wider text-muted-foreground">
        Score breakdown
      </h2>
      <p className="text-xs text-muted-foreground -mt-3">
        Tap a category to see supporting stats.
      </p>
      {DIMENSIONS.map(({ key, title }) => (
        <DimensionRow
          key={key}
          title={title}
          dimension={report[key] as ScoreDimension}
        />
      ))}
    </div>
  );
}
