import Link from "next/link";
import Header from "@/components/layout/Header";
import Footer from "@/components/layout/Footer";
import { ApiError, apiFetch } from "@/lib/api";
import type { CoverageResponse } from "@/types/api";
import CoverageViews from "@/components/coverage/CoverageViews";

export const dynamic = "force-dynamic";

export default async function CoveragePage() {
  let data: CoverageResponse | null = null;
  let error: string | null = null;

  try {
    data = await apiFetch<CoverageResponse>("/api/v1/coverage");
  } catch (err) {
    if (err instanceof ApiError) {
      error = err.message;
    } else {
      error = "Unable to load coverage data.";
    }
  }

  return (
    <div className="min-h-screen bg-background text-foreground font-sans">
      <Header />
      <main className="max-w-5xl mx-auto px-6 pt-28 pb-20">
        <div className="mb-10 space-y-3">
          <p className="text-sm font-semibold uppercase tracking-wide text-mint">
            National data
          </p>
          <h1 className="font-display text-4xl md:text-5xl font-bold tracking-tight">
            Coverage
          </h1>
          <p className="text-muted-foreground max-w-2xl text-base md:text-lg">
            How much of the 50 states + DC our batch data covers — overall and by
            state. No login required. Denominators match national ingest (full
            county registry, not only counties already loaded).
          </p>
        </div>

        {error && (
          <div
            className="rounded-lg border border-destructive/40 bg-destructive/5 px-4 py-3 text-sm"
            role="alert"
          >
            {error}
          </div>
        )}

        {!error && data?.empty_universe && (
          <div className="rounded-lg border border-border px-4 py-6 text-sm text-muted-foreground">
            National county registry is empty. Bootstrap{" "}
            <code className="text-foreground">geo_counties</code> before coverage
            percentages are meaningful.
          </div>
        )}

        {!error && data && !data.empty_universe && (
          <>
            <div className="mb-8 grid gap-4 sm:grid-cols-3">
              <StatCard
                label="Overall (mean of sources)"
                value={`${data.overall_pct.toFixed(1)}%`}
              />
              <StatCard
                label="Counties in registry"
                value={String(data.county_universe_count)}
              />
              <StatCard
                label="States + DC"
                value={String(data.state_universe_count)}
              />
            </div>
            <p
              className="mb-6 text-xs text-muted-foreground"
              suppressHydrationWarning
            >
              Snapshot{" "}
              {new Date(data.captured_at).toLocaleString("en-US", {
                dateStyle: "medium",
                timeStyle: "short",
                timeZone: "UTC",
              })}{" "}
              UTC
            </p>
            <CoverageViews
              sources={data.sources}
              states={data.states}
              overallPct={data.overall_pct}
            />
          </>
        )}

        <div className="mt-12">
          <Link
            href="/"
            className="text-sm font-semibold text-primary hover:opacity-90"
          >
            ← Back to search
          </Link>
        </div>
      </main>
      <Footer />
    </div>
  );
}

function StatCard({ label, value }: { label: string; value: string }) {
  return (
    <div className="rounded-xl border border-border bg-card/40 px-5 py-4">
      <p className="text-xs font-medium uppercase tracking-wide text-muted-foreground">
        {label}
      </p>
      <p className="mt-1 font-display text-3xl font-bold tabular-nums">{value}</p>
    </div>
  );
}
