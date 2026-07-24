import Header from "@/components/layout/Header";
import Footer from "@/components/layout/Footer";
import DiscoverMapClient from "@/components/discover/DiscoverMapClient";

/**
 * Server Component shell — async Header/Footer must stay outside any
 * "use client" module (auth()/headers need request scope).
 */
export default function DiscoverMapPage() {
  return (
    <div className="min-h-screen bg-background text-foreground font-sans">
      <Header />
      <main className="max-w-6xl mx-auto px-6 pt-28 pb-16">
        <DiscoverMapClient />
      </main>
      <Footer />
    </div>
  );
}
