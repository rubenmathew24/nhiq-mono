import { Sparkles } from "lucide-react";
import { aiContent } from "@/content/landing";

export default function AiInsightsSection() {
  return (
    <section id="ai" className="py-24 lg:py-32 bg-secondary border-y border-border">
      <div className="max-w-6xl mx-auto px-6 grid lg:grid-cols-[1.1fr_1fr] gap-14 items-start">
        <div className="lg:sticky lg:top-24">
          <p className="text-xs uppercase tracking-widest font-semibold text-accent-foreground mb-3">
            {aiContent.eyebrow}
          </p>
          <h2
            className="font-display text-4xl lg:text-5xl font-bold tracking-tight text-foreground text-balance"
            style={{ lineHeight: 1.08 }}
          >
            {aiContent.headline}
            <br />
            <span className="italic text-mint">{aiContent.headlineAccent}</span>
          </h2>
          <p className="mt-5 text-lg text-muted-foreground">{aiContent.subcopy}</p>

          <div className="mt-8 rounded-2xl bg-card border border-border p-6 shadow-lg shadow-primary/5">
            <div className="flex items-center gap-2 mb-4">
              <Sparkles className="w-4 h-4 text-accent" aria-hidden="true" />
              <span className="text-xs uppercase tracking-widest font-semibold text-foreground/60">
                AI narrative
              </span>
            </div>
            <p className="text-foreground leading-relaxed font-display text-lg">
              &ldquo;{aiContent.sampleQuote}&rdquo;
            </p>
          </div>
        </div>

        <div className="space-y-4">
          {aiContent.features.map((feature) => {
            const Icon = feature.icon;
            return (
              <div
                key={feature.title}
                className="flex gap-5 p-6 rounded-2xl border border-border bg-card hover:border-primary/20 transition-colors"
              >
                <div className="w-11 h-11 rounded-xl bg-primary text-primary-foreground grid place-items-center shrink-0">
                  <Icon className="w-5 h-5" aria-hidden="true" />
                </div>
                <div>
                  <h3 className="font-display text-lg font-bold text-foreground mb-1">
                    {feature.title}
                  </h3>
                  <p className="text-sm text-muted-foreground leading-relaxed">
                    {feature.description}
                  </p>
                </div>
              </div>
            );
          })}
        </div>
      </div>
    </section>
  );
}
