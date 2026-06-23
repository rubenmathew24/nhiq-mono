import { Sparkles } from "lucide-react";

interface ReportAiSummaryProps {
  narrative: string;
}

export default function ReportAiSummary({ narrative }: ReportAiSummaryProps) {
  return (
    <div className="rounded-2xl bg-card border border-border p-6">
      <div className="flex items-start gap-2">
        <Sparkles
          className="w-4 h-4 text-accent shrink-0 mt-0.5"
          aria-hidden="true"
        />
        <div>
          <p className="text-xs uppercase tracking-wider font-semibold text-muted-foreground mb-2">
            AI summary
          </p>
          <p className="text-sm text-muted-foreground leading-relaxed">
            <span className="text-foreground font-medium">Preview:</span>{" "}
            {narrative}
          </p>
          <p className="mt-3 text-[10px] uppercase tracking-wider text-muted-foreground/70">
            Sample scores — full neighborhood intelligence coming soon
          </p>
        </div>
      </div>
    </div>
  );
}
