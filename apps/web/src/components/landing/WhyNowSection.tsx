import { whyNowContent } from "@/content/landing";

export default function WhyNowSection() {
  return (
    <section className="py-24 lg:py-32 bg-secondary border-t border-border">
      <div className="max-w-6xl mx-auto px-6">
        <div className="max-w-2xl mb-14">
          <p className="text-xs uppercase tracking-widest font-semibold text-mint mb-3">
            {whyNowContent.eyebrow}
          </p>
          <h2
            className="font-display text-4xl lg:text-5xl font-bold tracking-tight text-foreground text-balance"
            style={{ lineHeight: 1.1 }}
          >
            {whyNowContent.headline}
          </h2>
        </div>

        <div className="grid md:grid-cols-2 gap-x-12 gap-y-10 auto-rows-fr">
          {whyNowContent.reasons.map((reason, index) => (
            <div key={reason.title} className="flex gap-6 h-full">
              <span className="font-display text-2xl font-bold text-accent-foreground/40 tabular-nums shrink-0">
                {String(index + 1).padStart(2, "0")}
              </span>
              <div>
                <h3 className="font-display text-xl font-bold text-foreground mb-2">
                  {reason.title}
                </h3>
                <p className="text-muted-foreground leading-relaxed">
                  {reason.description}
                </p>
              </div>
            </div>
          ))}
        </div>

        <blockquote
          className="mt-20 max-w-3xl border-l-2 border-accent pl-6 font-display text-2xl lg:text-3xl font-medium text-foreground italic"
          style={{ lineHeight: 1.3 }}
        >
          &ldquo;{whyNowContent.quote}&rdquo;
        </blockquote>
      </div>
    </section>
  );
}
