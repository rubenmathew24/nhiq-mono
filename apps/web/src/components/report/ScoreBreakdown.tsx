import ScoreBar from "@/components/ui/ScoreBar";
import { cn, scoreTextClass } from "@/lib/utils";
import type { NeighborhoodReport, ScoreDimension } from "@/types/api";

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

function DimensionRow({
  title,
  dimension,
}: {
  title: string;
  dimension: ScoreDimension;
}) {
  return (
    <div>
      <div className="flex items-center justify-between text-xs mb-1">
        <span className="text-foreground/70 font-medium">{title}</span>
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
      <p className="mt-2 text-xs text-muted-foreground leading-relaxed">
        {dimension.summary}
      </p>
    </div>
  );
}

export default function ScoreBreakdown({ report }: ScoreBreakdownProps) {
  return (
    <div className="rounded-2xl bg-card border border-border p-6 space-y-5">
      <h2 className="text-sm font-semibold uppercase tracking-wider text-muted-foreground">
        Score breakdown
      </h2>
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
