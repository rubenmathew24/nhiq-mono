import Link from "next/link";
import { notFound } from "next/navigation";
import { ArrowLeft } from "lucide-react";
import Header from "@/components/layout/Header";
import Footer from "@/components/layout/Footer";
import MapView from "@/components/report/MapView";
import ReportAiSummary from "@/components/report/ReportAiSummary";
import ScoreBreakdown from "@/components/report/ScoreBreakdown";
import ScoreSummary from "@/components/report/ScoreSummary";
import LookupActivityTouch from "@/components/report/LookupActivityTouch";
import { ApiError, apiFetch } from "@/lib/api";
import { auth } from "@/lib/auth";
import type { NeighborhoodReport } from "@/types/api";

interface ReportPageProps {
  params: Promise<{ addressId: string }>;
}

function ReportShell({
  isSignedIn,
  children,
}: {
  isSignedIn: boolean;
  children: React.ReactNode;
}) {
  return (
    <div className="min-h-screen bg-background text-foreground font-sans">
      <Header />
      <main className="max-w-3xl mx-auto px-6 py-32 text-center space-y-4">
        {children}
        <div className="flex flex-wrap items-center justify-center gap-4">
          {isSignedIn && (
            <Link
              href="/dashboard"
              className="inline-flex items-center gap-1.5 text-sm font-semibold text-primary hover:opacity-90"
            >
              <ArrowLeft className="w-4 h-4" aria-hidden="true" />
              Back to dashboard
            </Link>
          )}
          <Link
            href="/"
            className="inline-flex text-sm font-semibold text-muted-foreground hover:text-foreground"
          >
            Back to search
          </Link>
        </div>
      </main>
      <Footer />
    </div>
  );
}

export default async function ReportPage({ params }: ReportPageProps) {
  const { addressId } = await params;
  const session = await auth();
  const isSignedIn = !!session?.user;

  let report: NeighborhoodReport;
  try {
    report = await apiFetch<NeighborhoodReport>(
      `/api/v1/score/${addressId}`,
    );
  } catch (err) {
    if (err instanceof ApiError && err.code === "SCORE_UNAVAILABLE") {
      return (
        <ReportShell isSignedIn={isSignedIn}>
          <h1 className="text-2xl font-display font-bold">
            Score not available yet
          </h1>
          <p className="text-muted-foreground text-sm max-w-md mx-auto">
            {err.message ||
              "Neighborhood score is not available for this address yet."}
          </p>
        </ReportShell>
      );
    }

    if (err instanceof ApiError && err.status === 404) {
      notFound();
    }

    return (
      <ReportShell isSignedIn={isSignedIn}>
        <h1 className="text-2xl font-display font-bold">
          Unable to load this report
        </h1>
        <p className="text-muted-foreground text-sm">
          {err instanceof Error
            ? err.message
            : "The scoring service is temporarily unavailable."}
        </p>
      </ReportShell>
    );
  }

  return (
    <div className="min-h-screen bg-background text-foreground font-sans">
      <Header />
      {isSignedIn ? <LookupActivityTouch addressId={addressId} /> : null}
      <main className="max-w-5xl mx-auto px-6 pt-28 pb-16 space-y-8">
        {isSignedIn && (
          <Link
            href="/dashboard"
            className="inline-flex items-center gap-1.5 text-sm font-semibold text-muted-foreground hover:text-foreground transition-colors"
          >
            <ArrowLeft className="w-4 h-4" aria-hidden="true" />
            Back to dashboard
          </Link>
        )}

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
