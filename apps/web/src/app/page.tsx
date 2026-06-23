import Header from "@/components/layout/Header";
import Footer from "@/components/layout/Footer";
import HeroSection from "@/components/landing/HeroSection";
import ProblemSection from "@/components/landing/ProblemSection";
import ScoreDimensionsSection from "@/components/landing/ScoreDimensionsSection";
import AiInsightsSection from "@/components/landing/AiInsightsSection";
import PricingSection from "@/components/landing/PricingSection";
import WhyNowSection from "@/components/landing/WhyNowSection";
import FinalCtaSection from "@/components/landing/FinalCtaSection";

export default function HomePage() {
  return (
    <div className="min-h-screen bg-background text-foreground font-sans">
      <Header />
      <main>
        <HeroSection />
        <ProblemSection />
        <ScoreDimensionsSection />
        <AiInsightsSection />
        <PricingSection />
        <WhyNowSection />
        <FinalCtaSection />
      </main>
      <Footer />
    </div>
  );
}
