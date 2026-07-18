import { redirect } from "next/navigation";
import Header from "@/components/layout/Header";
import Footer from "@/components/layout/Footer";
import LookupList from "@/components/dashboard/LookupList";
import AddressSearch from "@/components/search/AddressSearch";
import { auth } from "@/lib/auth";
import { apiFetchServer } from "@/lib/api";
import type { LookupListResponse } from "@/types/api";

export const metadata = {
  title: "Dashboard — NeighborhoodInsight",
};

export default async function DashboardPage() {
  const session = await auth();
  if (!session?.user) {
    redirect("/login?callbackUrl=/dashboard");
  }

  let lookups: LookupListResponse = { items: [] };
  try {
    lookups = await apiFetchServer<LookupListResponse>("/api/v1/users/me/lookups", {
      headers: {
        Authorization: `Bearer ${session.accessToken ?? ""}`,
      },
    });
  } catch {
    // show empty state on fetch error
  }

  return (
    <div className="min-h-screen bg-background text-foreground font-sans">
      <Header />
      <main className="pt-32 pb-24">
        <div className="max-w-3xl mx-auto px-6">
          <div className="mb-8">
            <h1 className="font-display text-3xl font-bold tracking-tight text-foreground">
              Your saved lookups
            </h1>
            <p className="mt-2 text-muted-foreground text-sm">
              Search a new address or reopen one you&apos;ve already scored.
            </p>
          </div>

          <div className="mb-10">
            <AddressSearch />
          </div>

          <LookupList lookups={lookups.items} />
        </div>
      </main>
      <Footer />
    </div>
  );
}
