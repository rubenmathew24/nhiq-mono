import { scoreDimensions } from "@/content/landing";
import { cn } from "@/lib/utils";

const iconStyles = {
  mint: "bg-mint/15 text-mint",
  primary: "bg-primary/10 text-primary",
  accent: "bg-accent/18 text-accent-foreground",
};

export default function ScoreDimensionsSection() {
  return (
    <section id="scores" className="py-24 lg:py-32 bg-background">
      <div className="max-w-6xl mx-auto px-6">
        <div className="max-w-2xl">
          <p className="text-xs uppercase tracking-widest font-semibold text-mint mb-3">
            What we score
          </p>
          <h2
            className="font-display text-4xl lg:text-5xl font-bold tracking-tight text-foreground text-balance"
            style={{ lineHeight: 1.1 }}
          >
            Four scores. One number you can trust.
          </h2>
          <p className="mt-5 text-lg text-muted-foreground">
            We aggregate authoritative public government data into a single
            Neighborhood Score — with the receipts always one click away.
          </p>
        </div>

        <div className="mt-14 grid sm:grid-cols-2 gap-5 auto-rows-fr">
          {scoreDimensions.map((dim) => {
            const Icon = dim.icon;
            return (
              <div
                key={dim.title}
                className="group relative rounded-2xl border border-border bg-card p-7 hover:border-primary/30 hover:shadow-xl hover:shadow-primary/5 transition-all duration-300 h-full"
              >
                <div
                  className={cn(
                    "w-12 h-12 rounded-xl grid place-items-center mb-5",
                    iconStyles[dim.iconStyle],
                  )}
                >
                  <Icon className="w-6 h-6" aria-hidden="true" />
                </div>
                <h3 className="font-display text-xl font-bold text-foreground mb-2">
                  {dim.title}
                </h3>
                <p className="text-sm text-muted-foreground leading-relaxed mb-4">
                  {dim.description}
                </p>
                <p className="text-[11px] uppercase tracking-wider font-semibold text-foreground/50">
                  Sources · {dim.sources}
                </p>
              </div>
            );
          })}
        </div>
      </div>
    </section>
  );
}
