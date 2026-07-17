"use client";

import { useId, useRef, useState, type KeyboardEvent, type MouseEvent, type PointerEvent } from "react";
import ScoreBar from "@/components/ui/ScoreBar";
import { cn, scoreTextClass } from "@/lib/utils";
import type { Factor, NeighborhoodReport, ScoreDimension, SubScore } from "@/types/api";

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

/** Ignore click-to-toggle when the pointer moved this far (text drag-select). */
const CLICK_DRAG_THRESHOLD_PX = 5;

function factorValueClass(f: Factor): string {
  if (typeof f.tone_score === "number") {
    return scoreTextClass(f.tone_score);
  }
  if (f.impact === "positive") return "text-score-good";
  if (f.impact === "negative") return "text-score-poor";
  return "text-foreground/80";
}

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
  const pointerDown = useRef<{ x: number; y: number } | null>(null);
  const subs = dimension.sub_scores ?? [];
  const factors = dimension.factors ?? [];

  const toggle = () => setOpen((v) => !v);

  const onKeyDown = (e: KeyboardEvent<HTMLDivElement>) => {
    if (e.key === "Enter" || e.key === " ") {
      e.preventDefault();
      toggle();
    }
  };

  const onPointerDown = (e: PointerEvent<HTMLDivElement>) => {
    pointerDown.current = { x: e.clientX, y: e.clientY };
  };

  const onActivateClick = (e: MouseEvent<HTMLDivElement>) => {
    const start = pointerDown.current;
    pointerDown.current = null;
    if (start) {
      const dx = Math.abs(e.clientX - start.x);
      const dy = Math.abs(e.clientY - start.y);
      if (dx > CLICK_DRAG_THRESHOLD_PX || dy > CLICK_DRAG_THRESHOLD_PX) {
        return;
      }
    }
    const selected = typeof window !== "undefined" ? window.getSelection()?.toString() : "";
    if (selected && selected.length > 0) {
      return;
    }
    toggle();
  };

  // Whole-box activate + hover; text remains selectable (no select-none).
  // Drag-select / moved pointer does not toggle — see SC-014.
  return (
    <div
      role="button"
      tabIndex={0}
      data-category-box={title}
      className={cn(
        "w-full text-left rounded-xl border border-border/70 bg-muted/20 p-3.5",
        "transition-colors cursor-pointer",
        "hover:bg-muted/55 hover:border-border",
        "focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring",
        open && "border-border bg-muted/40",
      )}
      aria-expanded={open}
      aria-controls={panelId}
      aria-label={`${open ? "Collapse" : "Expand"} ${title} details`}
      onPointerDown={onPointerDown}
      onClick={onActivateClick}
      onKeyDown={onKeyDown}
    >
      <div className="flex items-center justify-between text-xs mb-1.5 gap-2">
        <span className="text-foreground font-medium flex items-center gap-1.5">
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
          className="mt-3 rounded-lg bg-card/80 border border-border/50 px-3 py-2.5 space-y-2"
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
                    "text-right font-medium tabular-nums",
                    factorValueClass(f),
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
    <div className="rounded-2xl bg-card border border-border p-6 space-y-3">
      <h2 className="text-sm font-semibold uppercase tracking-wider text-muted-foreground">
        Score breakdown
      </h2>
      <p className="text-xs text-muted-foreground -mt-1 mb-2">
        Tap a category box to see supporting stats.
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
