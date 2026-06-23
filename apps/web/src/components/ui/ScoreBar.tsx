import { cn, scoreBarClass } from "@/lib/utils";

interface ScoreBarProps {
  score: number;
  className?: string;
}

export default function ScoreBar({ score, className }: ScoreBarProps) {
  return (
    <div className={cn("h-1.5 rounded-full bg-muted overflow-hidden", className)}>
      <div
        className={cn(
          "h-full rounded-full transition-all duration-700",
          scoreBarClass(score),
        )}
        style={{ width: `${Math.min(100, Math.max(0, score))}%` }}
      />
    </div>
  );
}
