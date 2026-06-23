import Link from "next/link";
import { notFound } from "next/navigation";
import Header from "@/components/layout/Header";
import Footer from "@/components/layout/Footer";
import MapView from "@/components/report/MapView";
import ReportAiSummary from "@/components/report/ReportAiSummary";
import ScoreBreakdown from "@/components/report/ScoreBreakdown";
import ScoreSummary from "@/components/report/ScoreSummary";
import { ApiError, apiFetch } from "@/lib/api";
import type { NeighborhoodReport } from "@/types/api";

interface ReportPageProps {
  params: Promise<{ addressId: string }>;
}

export default async function ReportPage({ params }: ReportPageProps) {
  const { addressId } = await params;

  let report: NeighborhoodReport;
  try {
    report = await apiFetch<NeighborhoodReport>(
      `/api/v1/score/${addressId}`,
    );
  } catch (err) {
    if (err instanceof ApiError && err.status === 404) {
      notFound();
    }

    return (
      <div className="min-h-screen bg-background text-foreground font-sans">
        <Header />
        <main className="max-w-3xl mx-auto px-6 py-32 text-center space-y-4">
          <h1 className="text-2xl font-display font-bold">
            Unable to load this report
          </h1>
          <p className="text-muted-foreground text-sm">
            {err instanceof Error
              ? err.message
              : "The scoring service is temporarily unavailable."}
          </p>
          <Link
            href="/"
            className="inline-flex text-sm font-semibold text-primary hover:opacity-90"
          >
            Back to search
          </Link>
        </main>
        <Footer />
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-background text-foreground font-sans">
      <Header />
      <main className="max-w-5xl mx-auto px-6 pt-28 pb-16 space-y-8">
        <header className="space-y-1">
          <p className="text-xs uppercase tracking-wider font-semibold text-muted-foreground">
            Neighborhood report
          </p>
          <h1 className="text-3xl font-display font-bold tracking-tight">
            {report.address_normalized}
          </h1>
          {report.geoid && report.geoid !== "unknown" && (
            <p className="text-sm text-muted-foreground">
              Census tract {report.geoid}
            </p>
          )}
        </header>

        <MapView
          lat={report.latitude}
          lng={report.longitude}
          address={report.address_normalized}
        />
        <ScoreSummary report={report} />
        <ScoreBreakdown report={report} />
        <ReportAiSummary narrative={report.narrative} />
      </main>
      <Footer />
    </div>
  );
}
