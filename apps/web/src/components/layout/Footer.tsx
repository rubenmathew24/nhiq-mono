import Link from "next/link";
import { MapPin } from "lucide-react";
import { footerContent, navLinks } from "@/content/landing";
import { auth } from "@/lib/auth";

export default async function Footer() {
  const session = await auth();
  const isSignedIn = !!session?.user;
  const year = new Date().getFullYear();

  return (
    <footer className="border-t border-border bg-background py-12">
      <div className="max-w-7xl mx-auto px-6">
        <div className="flex flex-col md:flex-row items-start md:items-center justify-between gap-6">
          <div>
            <div className="flex items-center gap-2.5">
              <div className="w-8 h-8 rounded-lg bg-primary text-primary-foreground grid place-items-center">
                <MapPin className="w-4 h-4" strokeWidth={2.5} aria-hidden="true" />
              </div>
              <span className="font-display font-bold text-foreground">
                Neighborhood<span className="text-mint">IQ</span>
              </span>
            </div>
            <p className="mt-3 text-xs text-muted-foreground max-w-sm">
              {footerContent.tagline}
            </p>
          </div>

          <div className="flex items-center gap-6 text-sm text-muted-foreground">
            {navLinks.map((link) => (
              <a
                key={link.href}
                href={link.href}
                className="hover:text-foreground transition-colors"
              >
                {link.label}
              </a>
            ))}
            {!isSignedIn && (
              <Link href="/login" className="hover:text-foreground transition-colors">
                Sign in
              </Link>
            )}
          </div>
        </div>

        <p className="mt-8 text-xs text-muted-foreground">
          © {year} NeighborhoodIQ · Data sources: {footerContent.dataSources}
        </p>
      </div>
    </footer>
  );
}
