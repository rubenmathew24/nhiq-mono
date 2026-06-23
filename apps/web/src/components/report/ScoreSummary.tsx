import { cn, scoreGrade, scoreTextClass } from "@/lib/utils";
import type { NeighborhoodReport } from "@/types/api";

interface ScoreSummaryProps {
  report: NeighborhoodReport;
}

export default function ScoreSummary({ report }: ScoreSummaryProps) {
  return (
    <div className="rounded-2xl bg-card border border-border p-6 shadow-lg shadow-primary/10">
      <div className="flex items-start justify-between gap-6">
        <div>
          <p className="text-xs uppercase tracking-widest font-semibold text-muted-foreground">
            Neighborhood Score
          </p>
          <p className="mt-1 text-sm text-foreground/80">
            {report.address_normalized}
          </p>
          {report.geoid && report.geoid !== "unknown" && (
            <p className="mt-1 text-xs text-muted-foreground">
              Census tract {report.geoid}
            </p>
          )}
        </div>
        <div className="text-right shrink-0">
          <div
            className={cn(
              "font-display text-5xl font-bold leading-none",
              scoreTextClass(report.overall_score),
            )}
          >
            {Math.round(report.overall_score)}
          </div>
          <p
            className={cn(
              "text-[10px] uppercase tracking-wider font-semibold mt-1",
              scoreTextClass(report.overall_score),
            )}
          >
            {scoreGrade(report.overall_score)}
          </p>
        </div>
      </div>
    </div>
  );
}
