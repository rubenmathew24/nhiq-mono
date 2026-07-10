import Link from "next/link";
import { MapPin, ArrowRight } from "lucide-react";
import type { SavedLookup } from "@/types/api";

function formatDate(iso: string) {
  return new Date(iso).toLocaleDateString("en-US", {
    month: "short",
    day: "numeric",
    year: "numeric",
  });
}

export default function LookupList({ lookups }: { lookups: SavedLookup[] }) {
  if (lookups.length === 0) {
    return (
      <div className="rounded-2xl border border-border bg-card p-12 text-center">
        <div className="w-12 h-12 rounded-xl bg-muted grid place-items-center mx-auto mb-4">
          <MapPin className="w-5 h-5 text-muted-foreground" />
        </div>
        <p className="font-display font-semibold text-foreground">No saved lookups yet</p>
        <p className="mt-2 text-sm text-muted-foreground">
          Use the search bar above to score your first address.
        </p>
      </div>
    );
  }

  return (
    <ul className="divide-y divide-border rounded-2xl border border-border bg-card overflow-hidden">
      {lookups.map((lookup) => (
        <li key={`${lookup.user_id}-${lookup.address_id}-${lookup.looked_up_at}`}>
          <Link
            href={`/report/${lookup.address_id}`}
            className="flex items-center justify-between gap-4 px-6 py-4 hover:bg-muted/50 transition-colors group"
          >
            <div className="flex items-center gap-3 min-w-0">
              <div className="w-8 h-8 rounded-lg bg-primary/10 grid place-items-center shrink-0">
                <MapPin className="w-4 h-4 text-primary" />
              </div>
              <div className="min-w-0">
                <p className="text-sm font-medium text-foreground truncate">
                  {lookup.address_normalized}
                </p>
                <p className="text-xs text-muted-foreground">{formatDate(lookup.looked_up_at)}</p>
              </div>
            </div>
            <ArrowRight className="w-4 h-4 text-muted-foreground shrink-0 group-hover:text-foreground transition-colors" />
          </Link>
        </li>
      ))}
    </ul>
  );
}
