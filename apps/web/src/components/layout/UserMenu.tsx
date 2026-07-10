"use client";

import { useState, useRef, useEffect } from "react";
import Link from "next/link";
import { signOut, useSession } from "next-auth/react";
import { ChevronDown, LayoutDashboard, LogOut, GitCompare, CreditCard } from "lucide-react";
import { cn } from "@/lib/utils";

export default function UserMenu() {
  const { data: session } = useSession();
  const [open, setOpen] = useState(false);
  const ref = useRef<HTMLDivElement>(null);

  useEffect(() => {
    function handleClickOutside(e: MouseEvent) {
      if (ref.current && !ref.current.contains(e.target as Node)) {
        setOpen(false);
      }
    }
    document.addEventListener("mousedown", handleClickOutside);
    return () => document.removeEventListener("mousedown", handleClickOutside);
  }, []);

  if (!session?.user) return null;

  const name = session.user.name ?? session.user.email ?? "Account";
  const initial = name.charAt(0).toUpperCase();

  return (
    <div ref={ref} className="relative">
      <button
        onClick={() => setOpen((v) => !v)}
        className="flex items-center gap-2 rounded-xl px-3 py-2 text-sm font-medium text-foreground hover:bg-muted transition-colors"
        aria-expanded={open}
        aria-haspopup="true"
      >
        <span className="w-7 h-7 rounded-lg bg-primary text-primary-foreground grid place-items-center text-xs font-bold">
          {initial}
        </span>
        <span className="hidden sm:block">{name}</span>
        <ChevronDown
          className={cn("w-4 h-4 text-muted-foreground transition-transform", open && "rotate-180")}
        />
      </button>

      {open && (
        <div className="absolute right-0 top-full mt-2 w-48 rounded-xl border border-border bg-card shadow-lg py-1 z-50">
          <div className="px-3 py-2 border-b border-border mb-1">
            <p className="text-xs text-muted-foreground truncate">{session.user.email}</p>
          </div>

          <Link
            href="/dashboard"
            onClick={() => setOpen(false)}
            className="flex items-center gap-2.5 px-3 py-2 text-sm text-foreground hover:bg-muted transition-colors"
          >
            <LayoutDashboard className="w-4 h-4 text-muted-foreground" />
            Dashboard
          </Link>

          <Link
            href="/pricing"
            onClick={() => setOpen(false)}
            className="flex items-center gap-2.5 px-3 py-2 text-sm text-foreground hover:bg-muted transition-colors"
          >
            <CreditCard className="w-4 h-4 text-muted-foreground" />
            Plans & upgrade
          </Link>

          <Link
            href="/compare"
            onClick={() => setOpen(false)}
            className="flex items-center gap-2.5 px-3 py-2 text-sm text-foreground hover:bg-muted transition-colors"
          >
            <GitCompare className="w-4 h-4 text-muted-foreground" />
            Compare addresses
          </Link>

          <div className="border-t border-border mt-1 pt-1">
            <button
              onClick={() => signOut({ callbackUrl: "/" })}
              className="flex w-full items-center gap-2.5 px-3 py-2 text-sm text-foreground hover:bg-muted transition-colors"
            >
              <LogOut className="w-4 h-4 text-muted-foreground" />
              Sign out
            </button>
          </div>
        </div>
      )}
    </div>
  );
}
