import { pricingFootnote } from "@/content/landing";
import { auth } from "@/lib/auth";
import PricingTiersGrid, {
  formatTierLabel,
  resolveSessionTier,
} from "@/components/pricing/PricingTiersGrid";

export default async function PricingSection() {
  const session = await auth();
  const isSignedIn = !!session?.user;
  const currentTier = resolveSessionTier(session as { user?: { tier?: string }; tier?: string } | null);

  return (
    <section id="pricing" className="py-24 lg:py-32 bg-background">
      <div className="max-w-6xl mx-auto px-6">
        <div className="text-center max-w-2xl mx-auto mb-14">
          <p className="text-xs uppercase tracking-widest font-semibold text-mint mb-3">
            {isSignedIn ? "Upgrade" : "Pricing"}
          </p>
          <h2
            className="font-display text-4xl lg:text-5xl font-bold tracking-tight text-foreground text-balance"
            style={{ lineHeight: 1.1 }}
          >
            {isSignedIn
              ? "Choose the plan that fits your search."
              : "Less than a single home inspection."}
          </h2>
          <p className="mt-4 text-lg text-muted-foreground">
            {isSignedIn ? (
              <>
                You&apos;re on{" "}
                <span className="font-semibold text-foreground">
                  {formatTierLabel(currentTier)}
                </span>
                . Plan changes aren&apos;t live yet — browse options below.
              </>
            ) : (
              <>
                Built for buyers first. Agent, brokerage, and API plans available on
                request.
              </>
            )}
          </p>
        </div>

        <PricingTiersGrid
          mode={isSignedIn ? "upgrade" : "guest"}
          currentTier={currentTier}
        />

        <p className="mt-10 text-center text-sm text-muted-foreground">
          {pricingFootnote}
        </p>
      </div>
    </section>
  );
}
