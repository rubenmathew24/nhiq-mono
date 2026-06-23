import Link from "next/link";
import { MapPin } from "lucide-react";
import { navLinks } from "@/content/landing";
import { ButtonWithArrow } from "@/components/ui/Button";

export default function Header() {
  return (
    <nav className="absolute top-0 inset-x-0 z-30">
      <div className="max-w-7xl mx-auto px-6 h-20 flex items-center justify-between">
        <Link href="/" className="flex items-center gap-2.5">
          <div className="w-9 h-9 rounded-lg bg-primary text-primary-foreground grid place-items-center">
            <MapPin className="w-5 h-5" strokeWidth={2.5} aria-hidden="true" />
          </div>
          <span className="text-lg font-display font-bold tracking-tight text-foreground">
            Neighborhood<span className="text-mint">IQ</span>
          </span>
        </Link>

        <div className="hidden md:flex items-center gap-8 text-sm font-medium text-foreground/70">
          {navLinks.map((link) => (
            <a
              key={link.href}
              href={link.href}
              className="hover:text-foreground transition-colors"
            >
              {link.label}
            </a>
          ))}
        </div>

        <ButtonWithArrow href="#pricing" className="px-5 py-2.5">
          Get started
        </ButtonWithArrow>
      </div>
    </nav>
  );
}
