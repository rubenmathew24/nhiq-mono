import Image from "next/image";
import { MapPin } from "lucide-react";
import { heroContent } from "@/content/landing";
import AddressSearch from "@/components/search/AddressSearch";
import ScorePreviewCard from "@/components/ui/ScorePreviewCard";

export default function HeroSection() {
  return (
    <section id="hero" className="relative pt-32 pb-20 lg:pt-40 lg:pb-28 overflow-hidden">
      <div className="absolute -top-32 -right-32 w-[600px] h-[600px] rounded-full bg-accent/15 blur-3xl pointer-events-none" />
      <div className="absolute -bottom-40 -left-40 w-[500px] h-[500px] rounded-full bg-mint/10 blur-3xl pointer-events-none" />

      <div className="relative max-w-7xl mx-auto px-6 grid lg:grid-cols-2 gap-12 lg:gap-16 items-center">
        <div className="max-w-xl">
          <div className="inline-flex items-center gap-2 rounded-full bg-primary/5 border border-primary/10 px-3 py-1.5 text-xs font-medium text-primary mb-6">
            <span className="w-1.5 h-1.5 rounded-full bg-accent animate-pulse" />
            {heroContent.badge}
          </div>

          <h1
            className="font-display font-bold tracking-tight text-foreground text-5xl sm:text-6xl lg:text-[4.25rem] text-balance"
            style={{ lineHeight: 1.02 }}
          >
            {heroContent.headline}
            <span className="block text-mint italic font-medium">
              {heroContent.headlineAccent}
            </span>
          </h1>

          <p
            className="mt-6 text-lg text-muted-foreground"
            style={{ lineHeight: 1.6 }}
          >
            {heroContent.subcopy}
          </p>

          <div className="mt-8">
            <AddressSearch />
          </div>

          <p className="mt-4 text-xs text-muted-foreground">
            {heroContent.freeTierNote}
          </p>
        </div>

        <div className="relative">
          <div className="relative rounded-3xl overflow-hidden border border-primary/10 shadow-2xl shadow-primary/20">
            <Image
              src="/images/hero.jpg"
              alt="Aerial view of a suburban U.S. neighborhood"
              width={1280}
              height={720}
              className="w-full h-[360px] object-cover"
              priority
            />
            <div className="absolute inset-0 bg-gradient-to-t from-primary/80 via-primary/20 to-transparent" />
            <div className="absolute top-5 left-5 right-5 flex items-center justify-between text-primary-foreground">
              <div className="flex items-center gap-2">
                <MapPin className="w-4 h-4" aria-hidden="true" />
                <span className="text-sm font-medium">
                  2847 Walnut Grove · Austin, TX
                </span>
              </div>
              <span className="text-xs px-2 py-1 rounded-full bg-white/15 backdrop-blur-sm border border-white/20">
                SAMPLE
              </span>
            </div>
          </div>
          <ScorePreviewCard />
        </div>
      </div>
    </section>
  );
}
