import { Check } from "lucide-react";
import { pricingFootnote, pricingTiers } from "@/content/landing";
import { ButtonWithArrow } from "@/components/ui/Button";
import { cn } from "@/lib/utils";

export default function PricingSection() {
  return (
    <section id="pricing" className="py-24 lg:py-32 bg-background">
      <div className="max-w-6xl mx-auto px-6">
        <div className="text-center max-w-2xl mx-auto mb-14">
          <p className="text-xs uppercase tracking-widest font-semibold text-mint mb-3">
            Pricing
          </p>
          <h2
            className="font-display text-4xl lg:text-5xl font-bold tracking-tight text-foreground text-balance"
            style={{ lineHeight: 1.1 }}
          >
            Less than a single home inspection.
          </h2>
          <p className="mt-4 text-lg text-muted-foreground">
            Built for buyers first. Agent, brokerage, and API plans available on
            request.
          </p>
        </div>

        <div className="grid md:grid-cols-3 gap-5">
          {pricingTiers.map((tier) => (
            <div
              key={tier.name}
              className={cn(
                "relative rounded-3xl p-8 border transition-all",
                tier.highlighted
                  ? "bg-primary text-primary-foreground border-primary shadow-2xl shadow-primary/30 md:scale-[1.03]"
                  : "bg-card border-border hover:border-primary/30",
              )}
            >
              {tier.highlighted && (
                <span className="absolute -top-3 left-1/2 -translate-x-1/2 px-3 py-1 rounded-full bg-accent text-accent-foreground text-[10px] uppercase tracking-widest font-bold">
                  Most popular
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

              <ButtonWithArrow
                href="#hero"
                variant={tier.highlighted ? "accent" : "primary"}
                className="w-full"
              >
                {tier.cta}
              </ButtonWithArrow>
            </div>
          ))}
        </div>

        <p className="mt-10 text-center text-sm text-muted-foreground">
          {pricingFootnote}
        </p>
      </div>
    </section>
  );
}
