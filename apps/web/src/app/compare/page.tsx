import Link from "next/link";
import Header from "@/components/layout/Header";
import Footer from "@/components/layout/Footer";
import { ButtonWithArrow } from "@/components/ui/Button";

export const metadata = {
  title: "Compare — NeighborhoodInsight",
  description: "Side-by-side address comparison is coming soon.",
};

export default function ComparePage() {
  return (
    <div className="min-h-screen bg-background text-foreground font-sans">
      <Header />
      <main className="pt-32 pb-24">
        <div className="max-w-xl mx-auto px-6 text-center space-y-6">
          <p className="text-xs uppercase tracking-widest font-semibold text-mint">
            Compare
          </p>
          <h1 className="font-display text-3xl lg:text-4xl font-bold tracking-tight text-foreground">
            Feature coming soon
          </h1>
          <p className="text-muted-foreground text-sm leading-relaxed">
            Side-by-side neighborhood comparison is on the roadmap. In the
            meantime, score individual addresses from your dashboard or the home
            page.
          </p>
          <div className="flex flex-col sm:flex-row items-center justify-center gap-3 pt-2">
            <ButtonWithArrow href="/dashboard">Go to dashboard</ButtonWithArrow>
            <Link
              href="/"
              className="text-sm font-semibold text-primary hover:opacity-80 transition-opacity"
            >
              Back to home
            </Link>
          </div>
        </div>
      </main>
      <Footer />
    </div>
  );
}
