"use client";

type Props = {
  scoredCount: number;
  unscoredCount: number;
  truncated?: boolean;
};

export default function DiscoverCoverageBanner({
  scoredCount,
  unscoredCount,
  truncated = false,
}: Props) {
  if (scoredCount === 0) {
    return (
      <div
        className="rounded-xl border border-border bg-background/95 px-4 py-3 text-sm shadow"
        role="status"
      >
        <p className="font-medium text-foreground">
          No scored neighborhoods here yet
        </p>
        <p className="text-muted-foreground mt-1">
          We don&apos;t have overall neighborhood scores for this area. Try
          another city, or check back as coverage expands.
        </p>
      </div>
    );
  }

  if (unscoredCount > 0 || truncated) {
    return (
      <div
        className="rounded-xl border border-amber-500/30 bg-background/95 px-4 py-3 text-sm shadow"
        role="status"
      >
        <p className="font-medium text-foreground">Partial coverage in this area</p>
        <p className="text-muted-foreground mt-1">
          {unscoredCount > 0
            ? `Some tracts are gray because they don't have a score yet (${unscoredCount.toLocaleString()} unscored). `
            : null}
          {truncated
            ? "This map shows a capped set of tracts for performance — zoom to a smaller place for more detail."
            : null}
        </p>
      </div>
    );
  }

  return null;
}
