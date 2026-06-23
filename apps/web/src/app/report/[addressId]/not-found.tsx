import Link from "next/link";
import Header from "@/components/layout/Header";
import Footer from "@/components/layout/Footer";

export default function ReportNotFound() {
  return (
    <div className="min-h-screen bg-background text-foreground font-sans">
      <Header />
      <main className="max-w-3xl mx-auto px-6 py-32 text-center space-y-4">
        <h1 className="text-2xl font-display font-bold">Report not found</h1>
        <p className="text-muted-foreground text-sm">
          This address lookup may have expired or the link is invalid.
        </p>
        <Link
          href="/"
          className="inline-flex text-sm font-semibold text-primary hover:opacity-90"
        >
          Search a new address
        </Link>
      </main>
      <Footer />
    </div>
  );
}
