export default function DashboardLoading() {
  return (
    <div className="min-h-screen bg-background text-foreground font-sans">
      <div className="max-w-3xl mx-auto px-6 pt-32 pb-24" aria-busy="true" aria-label="Loading dashboard">
        <div className="mb-8 space-y-3 animate-pulse">
          <div className="h-9 w-64 rounded-lg bg-muted" />
          <div className="h-4 w-80 max-w-full rounded bg-muted" />
        </div>
        <div className="mb-10 h-14 rounded-2xl bg-muted animate-pulse" />
        <div className="rounded-2xl border border-border bg-card p-8 space-y-4 animate-pulse">
          <div className="h-5 w-40 rounded bg-muted" />
          <div className="h-4 w-full rounded bg-muted" />
          <div className="h-4 w-3/4 rounded bg-muted" />
        </div>
        <p className="mt-6 text-sm text-muted-foreground">Loading your saved lookups…</p>
      </div>
    </div>
  );
}
