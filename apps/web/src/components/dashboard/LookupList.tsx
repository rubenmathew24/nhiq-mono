"use client";

import { useMemo, useState, useCallback, useEffect, useRef } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { useSession } from "next-auth/react";
import { MapPin, MoreVertical, Star } from "lucide-react";
import { ApiError, apiFetch } from "@/lib/api";
import { cn, scoreTextClass } from "@/lib/utils";
import type { SavedLookup } from "@/types/api";

function formatDate(iso: string) {
  if (!iso) return "";
  return new Date(iso).toLocaleDateString("en-US", {
    month: "short",
    day: "numeric",
    year: "numeric",
  });
}

function LeadingScore({
  score,
  favorited,
}: {
  score: number | null;
  favorited: boolean;
}) {
  return (
    <div className="relative shrink-0 w-11 h-11 rounded-xl bg-primary/10 grid place-items-center">
      {score == null || Number.isNaN(score) ? (
        <span className="text-sm font-semibold text-muted-foreground tabular-nums">
          —
        </span>
      ) : (
        <span
          className={cn(
            "text-base font-bold tabular-nums leading-none",
            scoreTextClass(score),
          )}
        >
          {Math.round(score)}
        </span>
      )}
      {favorited ? (
        <span
          className="absolute -top-1 -right-1 rounded-full bg-card p-0.5 shadow-sm border border-border"
          aria-label="Favorited"
          title="Favorited"
        >
          <Star className="w-3 h-3 text-primary fill-primary" />
        </span>
      ) : null}
    </div>
  );
}

function LookupRow({
  lookup,
  onChanged,
}: {
  lookup: SavedLookup;
  onChanged: () => void;
}) {
  const { data: session } = useSession();
  const [menuOpen, setMenuOpen] = useState(false);
  const [busy, setBusy] = useState(false);
  const [confirmDelete, setConfirmDelete] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const menuRef = useRef<HTMLDivElement>(null);

  const token = session?.accessToken;

  const closeMenu = useCallback(() => {
    setMenuOpen(false);
    setConfirmDelete(false);
    setError(null);
  }, []);

  useEffect(() => {
    if (!menuOpen) return;
    const onPointer = (e: MouseEvent) => {
      if (!menuRef.current?.contains(e.target as Node)) {
        closeMenu();
      }
    };
    const onKey = (e: KeyboardEvent) => {
      if (e.key === "Escape") closeMenu();
    };
    document.addEventListener("mousedown", onPointer);
    document.addEventListener("keydown", onKey);
    return () => {
      document.removeEventListener("mousedown", onPointer);
      document.removeEventListener("keydown", onKey);
    };
  }, [menuOpen, closeMenu]);

  const favorite = async () => {
    if (!token) return;
    setBusy(true);
    setError(null);
    try {
      await apiFetch(`/api/v1/users/me/lookups/${lookup.address_id}`, {
        method: "PATCH",
        token,
        body: JSON.stringify({ is_favorite: !lookup.is_favorite }),
      });
      closeMenu();
      onChanged();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Could not update favorite.");
    } finally {
      setBusy(false);
    }
  };

  const remove = async () => {
    if (!token) return;
    if (lookup.is_favorite) {
      setError("Unfavorite this address before deleting it.");
      setConfirmDelete(false);
      return;
    }
    setBusy(true);
    setError(null);
    try {
      await apiFetch(`/api/v1/users/me/lookups/${lookup.address_id}`, {
        method: "DELETE",
        token,
      });
      closeMenu();
      onChanged();
    } catch (err) {
      if (err instanceof ApiError && err.status === 404) {
        closeMenu();
        onChanged();
        return;
      }
      if (err instanceof ApiError && err.status === 409) {
        setConfirmDelete(false);
        setError(err.message);
        return;
      }
      setError(err instanceof Error ? err.message : "Could not delete address.");
    } finally {
      setBusy(false);
    }
  };

  return (
    <li className="relative flex items-center gap-2 px-4 py-3 hover:bg-muted/40 transition-colors">
      <Link
        href={`/report/${lookup.address_id}`}
        className="flex items-center gap-3 min-w-0 flex-1"
      >
        <LeadingScore score={lookup.overall_score} favorited={lookup.is_favorite} />
        <div className="min-w-0 flex-1">
          <p className="text-sm font-medium text-foreground truncate">
            {lookup.address_normalized}
          </p>
          <p className="text-xs text-muted-foreground">
            {formatDate(lookup.last_activity_at || lookup.looked_up_at)}
          </p>
        </div>
      </Link>

      <div className="relative shrink-0" ref={menuRef}>
        <button
          type="button"
          aria-label="Address actions"
          aria-expanded={menuOpen}
          disabled={busy}
          className="p-2 rounded-lg text-muted-foreground hover:bg-muted hover:text-foreground"
          onClick={() => {
            if (menuOpen) {
              closeMenu();
              return;
            }
            setMenuOpen(true);
            setConfirmDelete(false);
            setError(null);
          }}
        >
          <MoreVertical className="w-4 h-4" />
        </button>
        {menuOpen ? (
          <div className="absolute right-0 top-full z-20 mt-1 w-48 rounded-xl border border-border bg-card shadow-lg py-1">
            {!confirmDelete ? (
              <>
                <button
                  type="button"
                  className="w-full text-left px-3 py-2 text-sm hover:bg-muted/60"
                  onClick={() => void favorite()}
                  disabled={busy}
                >
                  {lookup.is_favorite ? "Unfavorite" : "Favorite"}
                </button>
                {lookup.is_favorite ? (
                  <p className="px-3 py-2 text-xs text-muted-foreground">
                    Unfavorite before you can delete.
                  </p>
                ) : (
                  <button
                    type="button"
                    className="w-full text-left px-3 py-2 text-sm text-destructive hover:bg-muted/60"
                    onClick={() => setConfirmDelete(true)}
                    disabled={busy}
                  >
                    Delete
                  </button>
                )}
              </>
            ) : (
              <div className="px-3 py-2 space-y-2">
                <p className="text-xs text-muted-foreground">
                  Remove this address from your list?
                </p>
                <div className="flex gap-2">
                  <button
                    type="button"
                    className="flex-1 text-xs font-semibold rounded-lg bg-destructive text-destructive-foreground py-1.5"
                    onClick={() => void remove()}
                    disabled={busy}
                  >
                    Remove
                  </button>
                  <button
                    type="button"
                    className="flex-1 text-xs font-semibold rounded-lg border border-border py-1.5"
                    onClick={() => closeMenu()}
                    disabled={busy}
                  >
                    Cancel
                  </button>
                </div>
              </div>
            )}
            {error ? (
              <p className="px-3 pb-2 text-xs text-destructive">{error}</p>
            ) : null}
          </div>
        ) : null}
      </div>
    </li>
  );
}

function Column({
  title,
  empty,
  items,
  onChanged,
}: {
  title: string;
  empty: string;
  items: SavedLookup[];
  onChanged: () => void;
}) {
  return (
    <section className="space-y-3 min-w-0">
      <h2 className="font-display text-lg font-semibold tracking-tight">
        {title}
      </h2>
      {items.length === 0 ? (
        <div className="rounded-2xl border border-border bg-card p-8 text-center">
          <p className="text-sm text-muted-foreground">{empty}</p>
        </div>
      ) : (
        <ul className="divide-y divide-border rounded-2xl border border-border bg-card overflow-visible">
          {items.map((lookup) => (
            <LookupRow
              key={`${title}-${lookup.address_id}`}
              lookup={lookup}
              onChanged={onChanged}
            />
          ))}
        </ul>
      )}
    </section>
  );
}

export default function LookupList({
  lookups: initial,
}: {
  lookups: SavedLookup[];
}) {
  const router = useRouter();
  const { data: session } = useSession();
  const [lookups, setLookups] = useState(initial);

  useEffect(() => {
    setLookups(initial);
  }, [initial]);

  const refresh = useCallback(async () => {
    if (!session?.accessToken) {
      router.refresh();
      return;
    }
    try {
      const data = await apiFetch<{ items: SavedLookup[] }>(
        "/api/v1/users/me/lookups",
        { token: session.accessToken },
      );
      setLookups(data.items ?? []);
    } catch {
      router.refresh();
    }
  }, [router, session?.accessToken]);

  const favorites = useMemo(
    () =>
      [...lookups]
        .filter((l) => l.is_favorite)
        .sort((a, b) =>
          (b.last_activity_at || "").localeCompare(a.last_activity_at || ""),
        ),
    [lookups],
  );

  const recent = useMemo(
    () =>
      [...lookups].sort((a, b) =>
        (b.last_activity_at || "").localeCompare(a.last_activity_at || ""),
      ),
    [lookups],
  );

  if (lookups.length === 0) {
    return (
      <div className="rounded-2xl border border-border bg-card p-12 text-center">
        <div className="w-12 h-12 rounded-xl bg-muted grid place-items-center mx-auto mb-4">
          <MapPin className="w-5 h-5 text-muted-foreground" />
        </div>
        <p className="font-display font-semibold text-foreground">
          No saved lookups yet
        </p>
        <p className="mt-2 text-sm text-muted-foreground">
          Use the search bar above to score your first address.
        </p>
      </div>
    );
  }

  return (
    <div className="grid gap-10 md:grid-cols-2">
      <Column
        title="Favorites"
        empty="Star an address from Recent to pin it here."
        items={favorites}
        onChanged={() => void refresh()}
      />
      <Column
        title="Recent"
        empty="Addresses you score will show up here."
        items={recent}
        onChanged={() => void refresh()}
      />
    </div>
  );
}
