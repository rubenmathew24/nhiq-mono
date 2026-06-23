import { Sparkles } from "lucide-react";
import { scorePreview } from "@/content/landing";
import ScoreBar from "@/components/ui/ScoreBar";
import { cn, scoreTextClass } from "@/lib/utils";

export default function ScorePreviewCard() {
  return (
    <div className="relative lg:absolute lg:-bottom-12 lg:-left-10 mt-[-60px] lg:mt-0 mx-4 lg:mx-0 lg:w-[420px] rounded-2xl bg-card border border-border p-6 shadow-2xl shadow-primary/15">
      <p className="text-[10px] uppercase tracking-wider font-semibold text-muted-foreground mb-4">
        {scorePreview.label}
      </p>
      <div className="flex items-start justify-between mb-5">
        <div>
          <p className="text-xs uppercase tracking-widest font-semibold text-muted-foreground">
            Neighborhood Score
          </p>
          <p className="mt-1 text-sm text-foreground/80">{scorePreview.address}</p>
        </div>
        <div className="text-right">
          <div
            className={cn(
              "font-display text-5xl font-bold leading-none",
              scoreTextClass(scorePreview.overall),
            )}
          >
            {scorePreview.overall}
          </div>
          <p
            className={cn(
              "text-[10px] uppercase tracking-wider font-semibold mt-1",
              scoreTextClass(scorePreview.overall),
            )}
          >
            {scorePreview.rating}
          </p>
        </div>
      </div>
      <div className="space-y-3">
        {scorePreview.dimensions.map((dim) => (
          <div key={dim.name}>
            <div className="flex items-center justify-between text-xs mb-1">
              <span className="text-foreground/70 font-medium">{dim.name}</span>
              <span
                className={cn(
                  "font-display font-semibold tabular-nums",
                  scoreTextClass(dim.score),
                )}
              >
                {dim.score}
              </span>
            </div>
            <ScoreBar score={dim.score} />
          </div>
        ))}
      </div>
      <div className="mt-5 pt-5 border-t border-border flex items-start gap-2">
        <Sparkles className="w-4 h-4 text-accent shrink-0 mt-0.5" aria-hidden="true" />
        <p className="text-xs text-muted-foreground leading-relaxed">
          <span className="text-foreground font-medium">AI summary:</span>{" "}
          {scorePreview.aiSummary}
        </p>
      </div>
    </div>
  );
}
