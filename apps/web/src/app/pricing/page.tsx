import { redirect } from "next/navigation";
import Header from "@/components/layout/Header";
import Footer from "@/components/layout/Footer";
import PricingTiersGrid, {
  formatTierLabel,
  resolveSessionTier,
} from "@/components/pricing/PricingTiersGrid";
import { pricingFootnote } from "@/content/landing";
import { auth } from "@/lib/auth";

export const metadata = {
  title: "Upgrade — NeighborhoodIQ",
  description: "Upgrade your NeighborhoodIQ plan for unlimited AI-powered reports.",
};

export default async function PricingPage() {
  const session = await auth();
  if (!session?.user) {
    redirect("/login?callbackUrl=/pricing");
  }

  const currentTier = resolveSessionTier(session as { user?: { tier?: string }; tier?: string });

  return (
    <div className="min-h-screen bg-background text-foreground font-sans">
      <Header />
      <main className="pt-32 pb-24">
        <div className="max-w-6xl mx-auto px-6">
          <div className="text-center max-w-2xl mx-auto mb-16">
            <p className="text-xs uppercase tracking-widest font-semibold text-mint mb-3">
              Upgrade
            </p>
            <h1
              className="font-display text-4xl lg:text-5xl font-bold tracking-tight text-foreground text-balance"
              style={{ lineHeight: 1.1 }}
            >
              Choose the plan that fits your search.
            </h1>
            <p className="mt-5 text-lg text-muted-foreground">
              You&apos;re on{" "}
              <span className="font-semibold text-foreground">
                {formatTierLabel(currentTier)}
              </span>
              . Plan changes aren&apos;t live yet — browse options below.
            </p>
          </div>

          <PricingTiersGrid mode="upgrade" currentTier={currentTier} />

          <p className="mt-10 text-center text-sm text-muted-foreground">{pricingFootnote}</p>
        </div>
      </main>
      <Footer />
    </div>
  );
}
