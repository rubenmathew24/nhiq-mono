import { problemContent } from "@/content/landing";

export default function ProblemSection() {
  return (
    <section className="py-24 lg:py-32 lg:pt-44 bg-primary text-primary-foreground">
      <div className="max-w-5xl mx-auto px-6">
        <p className="text-xs uppercase tracking-widest font-semibold text-accent mb-4">
          {problemContent.eyebrow}
        </p>
        <h2
          className="font-display text-3xl sm:text-4xl lg:text-4xl xl:text-5xl font-bold tracking-tight text-balance"
          style={{ lineHeight: 1.1 }}
        >
          {problemContent.headline}
          <br className="hidden md:block" />
          <span className="text-accent">{problemContent.headlineAccent}</span>
        </h2>
        <p className="mt-6 max-w-2xl text-primary-foreground/70 text-lg">
          {problemContent.subcopy}
        </p>

        <div className="mt-12 grid sm:grid-cols-2 gap-4 auto-rows-fr">
          {problemContent.questions.map((question) => (
            <div
              key={question}
              className="flex items-start gap-3 p-5 rounded-xl border border-primary-foreground/10 bg-primary-foreground/[0.03] h-full"
            >
              <span className="font-display text-2xl font-bold text-accent leading-none">
                ?
              </span>
              <p className="text-sm text-primary-foreground/85 leading-relaxed">
                {question}
              </p>
            </div>
          ))}
        </div>

        <p className="mt-10 text-lg font-display font-medium">
          {problemContent.closing}{" "}
          <span className="text-accent italic">{problemContent.closingAccent}</span>
        </p>
      </div>
    </section>
  );
}
