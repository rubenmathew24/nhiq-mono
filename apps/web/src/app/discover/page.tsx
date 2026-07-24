import Header from "@/components/layout/Header";
import Footer from "@/components/layout/Footer";
import DiscoverPlaceSearch from "@/components/discover/DiscoverPlaceSearch";

export default function DiscoverPage() {
  return (
    <div className="min-h-screen bg-background text-foreground font-sans">
      <Header />
      <main className="max-w-3xl mx-auto px-6 pt-28 pb-20">
        <div className="mb-10 space-y-3">
          <p className="text-sm font-semibold uppercase tracking-wide text-mint">
            Explore
          </p>
          <h1 className="font-display text-4xl md:text-5xl font-bold tracking-tight">
            Discover
          </h1>
          <p className="text-muted-foreground max-w-2xl text-base md:text-lg">
            Search a U.S. city and explore neighborhood scores on a map —
            census tracts colored by how they compare within that place.
            No account needed.
          </p>
        </div>
        <DiscoverPlaceSearch />
      </main>
      <Footer />
    </div>
  );
}
