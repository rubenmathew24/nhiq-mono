import { Check } from "lucide-react";
import { pricingTiers } from "@/content/landing";
import Button, { ButtonWithArrow } from "@/components/ui/Button";
import { cn } from "@/lib/utils";
import type { UserTier } from "@/types/api";

export const tierNameToSession: Record<string, UserTier> = {
  Free: "free",
  Buyer: "buyer",
  "Buyer Pro": "buyer_pro",
};

export function formatTierLabel(tier: string | undefined): string {
  if (!tier || tier === "free") return "Free";
  if (tier === "buyer") return "Buyer";
  if (tier === "buyer_pro") return "Buyer Pro";
  return tier;
}

export function resolveSessionTier(session: {
  user?: { tier?: string } | null;
  tier?: string;
} | null): string {
  return session?.user?.tier ?? session?.tier ?? "free";
}

type PricingTiersGridProps = {
  /** Guest marketing CTAs vs signed-in upgrade placeholders */
  mode: "guest" | "upgrade";
  currentTier?: string;
};

export default function PricingTiersGrid({
  mode,
  currentTier = "free",
}: PricingTiersGridProps) {
  return (
    <div className="grid md:grid-cols-3 gap-5">
      {pricingTiers.map((tier) => {
        const isCurrent =
          mode === "upgrade" && tierNameToSession[tier.name] === currentTier;

        return (
          <div
            key={tier.name}
            className={cn(
              "relative rounded-3xl p-8 border transition-all",
              tier.highlighted
                ? "bg-primary text-primary-foreground border-primary shadow-2xl shadow-primary/30 md:scale-[1.03]"
                : "bg-card border-border",
              mode === "guest" && !tier.highlighted && "hover:border-primary/30",
              isCurrent && "ring-2 ring-mint ring-offset-2 ring-offset-background",
            )}
          >
            {tier.highlighted && !isCurrent && (
              <span className="absolute -top-3 left-1/2 -translate-x-1/2 px-3 py-1 rounded-full bg-accent text-accent-foreground text-[10px] uppercase tracking-widest font-bold">
                Most popular
              </span>
            )}
            {isCurrent && (
              <span
                className={cn(
                  "absolute -top-3 left-1/2 -translate-x-1/2 px-3 py-1 rounded-full text-[10px] uppercase tracking-widest font-bold",
                  tier.highlighted
                    ? "bg-accent text-accent-foreground"
                    : "bg-mint text-mint-foreground",
                )}
              >
                Current plan
              </span>
            )}

            <h3 className="font-display text-xl font-bold mb-1">{tier.name}</h3>
            <p
              className={cn(
                "text-sm mb-6",
                tier.highlighted
                  ? "text-primary-foreground/70"
                  : "text-muted-foreground",
              )}
            >
              {tier.description}
            </p>

            <div className="flex items-baseline gap-1 mb-6">
              <span className="font-display text-5xl font-bold">{tier.price}</span>
              <span
                className={cn(
                  "text-sm",
                  tier.highlighted
                    ? "text-primary-foreground/60"
                    : "text-muted-foreground",
                )}
              >
                {tier.period}
              </span>
            </div>

            <ul className="space-y-3 mb-8">
              {tier.features.map((feature) => (
                <li key={feature} className="flex items-start gap-2.5 text-sm">
                  <Check
                    className={cn(
                      "w-4 h-4 mt-0.5 shrink-0",
                      tier.highlighted ? "text-accent" : "text-mint",
                    )}
                    aria-hidden="true"
                  />
                  <span
                    className={
                      tier.highlighted
                        ? "text-primary-foreground/90"
                        : "text-foreground/80"
                    }
                  >
                    {feature}
                  </span>
                </li>
              ))}
            </ul>

            {mode === "guest" && tier.name === "Free" ? (
              <ButtonWithArrow
                href="/register"
                variant={tier.highlighted ? "accent" : "primary"}
                className="w-full"
              >
                {tier.cta}
              </ButtonWithArrow>
            ) : mode === "guest" ? (
              /* Paid plans shown for marketing; checkout / paid signup not live yet */
              <Button
                type="button"
                variant={tier.highlighted ? "accent" : "primary"}
                className="w-full opacity-80 cursor-not-allowed"
                disabled
                aria-disabled="true"
              >
                Coming soon
              </Button>
            ) : (
              /* UI-only: upgrade checkout not wired yet */
              <Button
                type="button"
                variant={tier.highlighted ? "accent" : "primary"}
                className="w-full opacity-80 cursor-not-allowed"
                disabled
                aria-disabled="true"
              >
                {isCurrent ? "Current plan" : "Coming soon"}
              </Button>
            )}
          </div>
        );
      })}
    </div>
  );
}
