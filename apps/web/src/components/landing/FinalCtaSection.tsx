import { FileText } from "lucide-react";
import { finalCtaContent } from "@/content/landing";
import { ButtonWithArrow } from "@/components/ui/Button";

export default function FinalCtaSection() {
  return (
    <section className="relative overflow-hidden py-28 bg-primary text-primary-foreground">
      <div className="absolute -top-40 -right-40 w-[500px] h-[500px] rounded-full bg-accent/20 blur-3xl pointer-events-none" />

      <div className="relative max-w-3xl mx-auto px-6 text-center">
        <FileText
          className="w-10 h-10 mx-auto text-accent mb-6"
          strokeWidth={1.5}
          aria-hidden="true"
        />
        <h2
          className="font-display text-4xl lg:text-5xl font-bold tracking-tight text-balance"
          style={{ lineHeight: 1.1 }}
        >
          {finalCtaContent.headline}
          <span className="block text-accent italic">
            {finalCtaContent.headlineAccent}
          </span>
        </h2>
        <p className="mt-5 text-lg text-primary-foreground/75 max-w-xl mx-auto">
          {finalCtaContent.subcopy}
        </p>
        <ButtonWithArrow
          href="#hero"
          variant="accent"
          className="mt-10 px-8 py-4 text-sm font-bold"
        >
          {finalCtaContent.cta}
        </ButtonWithArrow>
      </div>
    </section>
  );
}
