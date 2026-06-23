# 02 — Next.js Frontend

> **Claude instructions:** This document defines the complete frontend architecture. Work through sections in order. All code goes in `apps/web/`. Reference `docs/00-project-overview.md` for API endpoints and environment variables.

---

## Stack

- **Next.js 14** — App Router, Server Components, TypeScript
- **Tailwind CSS** — all styling
- **Auth.js (next-auth v5)** — authentication
- **Mapbox GL JS** — map rendering
- **Zod** — API response validation
- **SWR** — client-side data fetching with caching

---

## Folder Structure

```
apps/web/
├── src/
│   ├── app/                          # App Router pages
│   │   ├── layout.tsx                # Root layout (fonts, providers)
│   │   ├── page.tsx                  # Homepage / address search
│   │   ├── (auth)/
│   │   │   ├── login/page.tsx
│   │   │   └── register/page.tsx
│   │   ├── dashboard/
│   │   │   └── page.tsx              # Saved lookups
│   │   ├── report/
│   │   │   └── [addressId]/
│   │   │       └── page.tsx          # Full neighborhood report
│   │   ├── compare/
│   │   │   └── page.tsx              # Side-by-side comparison
│   │   └── api/
│   │       └── auth/
│   │           └── [...nextauth]/
│   │               └── route.ts      # Auth.js handler
│   ├── components/
│   │   ├── ui/                       # Primitive UI components
│   │   │   ├── Button.tsx
│   │   │   ├── Card.tsx
│   │   │   ├── Badge.tsx
│   │   │   ├── ScoreRing.tsx         # Circular score display
│   │   │   └── LoadingSpinner.tsx
│   │   ├── search/
│   │   │   ├── AddressSearch.tsx     # Main address input
│   │   │   └── SearchSuggestions.tsx
│   │   ├── report/
│   │   │   ├── ScoreSummary.tsx      # Top-level score cards
│   │   │   ├── ScoreBreakdown.tsx    # Detailed per-dimension
│   │   │   ├── NarrativePanel.tsx    # AI-generated text
│   │   │   ├── TrendChart.tsx        # Score over time
│   │   │   ├── MapView.tsx           # Mapbox map
│   │   │   └── CompareBanner.tsx     # "Compare to another address"
│   │   ├── layout/
│   │   │   ├── Header.tsx
│   │   │   ├── Footer.tsx
│   │   │   └── UserMenu.tsx
│   │   └── paywall/
│   │       └── UpgradePrompt.tsx     # Freemium gate
│   ├── lib/
│   │   ├── api.ts                    # Typed API fetch wrapper
│   │   ├── auth.ts                   # Auth.js config
│   │   └── utils.ts                  # Helpers (cn, formatScore, etc.)
│   ├── types/
│   │   └── api.ts                    # TypeScript types mirroring API schemas
│   └── hooks/
│       ├── useScore.ts               # SWR hook for score data
│       └── useAddressSearch.ts       # Debounced address autocomplete
├── public/
│   └── logo.svg
├── next.config.ts
├── tailwind.config.ts
└── package.json
```

---

## Step 1: Install Dependencies

```bash
cd apps/web
npm install next-auth@beta
npm install @auth/prisma-adapter       # if using Prisma (optional)
npm install swr zod
npm install mapbox-gl
npm install @types/mapbox-gl --save-dev
npm install clsx tailwind-merge       # for cn() utility
npm install lucide-react               # icons
npm install recharts                   # trend charts
```

---

## Step 2: API Client (`apps/web/src/lib/api.ts`)

This is the single place all API calls originate. Never call `fetch` directly in components.

```typescript
const API_BASE = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

type ApiOptions = RequestInit & {
  token?: string;
};

export async function apiFetch<T>(
  path: string,
  options: ApiOptions = {}
): Promise<T> {
  const { token, ...fetchOptions } = options;

  const headers: HeadersInit = {
    "Content-Type": "application/json",
    ...(token ? { Authorization: `Bearer ${token}` } : {}),
    ...fetchOptions.headers,
  };

  const res = await fetch(`${API_BASE}${path}`, {
    ...fetchOptions,
    headers,
  });

  if (!res.ok) {
    const error = await res.json().catch(() => ({ detail: "Unknown error" }));
    throw new Error(error.detail ?? `API error ${res.status}`);
  }

  return res.json() as Promise<T>;
}
```

---

## Step 3: TypeScript Types (`apps/web/src/types/api.ts`)

Keep these in sync with FastAPI Pydantic schemas in `apps/api/app/schemas/`.

```typescript
export type UserTier = "free" | "buyer" | "buyer_pro" | "agent" | "brokerage";

export interface User {
  id: string;
  email: string;
  full_name: string | null;
  tier: UserTier;
  lookup_count_this_month: number;
}

export interface ScoreDimension {
  score: number;          // 0-100
  label: string;
  summary: string;        // 1-2 sentence plain-English summary
  factors: Factor[];
}

export interface Factor {
  name: string;
  value: string;
  impact: "positive" | "negative" | "neutral";
}

export interface NeighborhoodReport {
  address: string;
  address_normalized: string;
  geoid: string;           // Census tract FIPS
  latitude: number;
  longitude: number;
  overall_score: number;
  healthcare: ScoreDimension;
  safety: ScoreDimension;
  environment: ScoreDimension;
  education: ScoreDimension;
  economic: ScoreDimension;
  narrative: string;       // Full AI-generated narrative (Buyer tier+)
  data_vintage: string;    // e.g. "2024-Q3"
  computed_at: string;     // ISO timestamp
}

export interface CompareReport {
  address_a: NeighborhoodReport;
  address_b: NeighborhoodReport;
  ai_commentary: string;   // Trade-off explainer (Buyer tier+)
}

export interface TrendPoint {
  period: string;          // "2022-Q1"
  overall_score: number;
  healthcare_score: number;
  safety_score: number;
  environment_score: number;
  education_score: number;
  economic_score: number;
}

export interface LookupResponse {
  address_id: string;
  status: "cached" | "computing" | "ready";
  report?: NeighborhoodReport;
}
```

---

## Step 4: Homepage / Address Search (`apps/web/src/app/page.tsx`)

```typescript
import AddressSearch from "@/components/search/AddressSearch";

export default function HomePage() {
  return (
    <main className="min-h-screen bg-slate-950 flex flex-col items-center justify-center px-4">
      <div className="max-w-2xl w-full text-center space-y-8">
        <h1 className="text-5xl font-bold text-white tracking-tight">
          Know Your Neighborhood
          <span className="text-blue-400"> Before You Buy</span>
        </h1>
        <p className="text-slate-400 text-xl">
          AI-powered scores for healthcare, safety, schools, and more —
          for any U.S. address.
        </p>
        <AddressSearch />
        <p className="text-slate-600 text-sm">
          3 free lookups per month. No credit card required.
        </p>
      </div>
    </main>
  );
}
```

---

## Step 5: Address Search Component (`apps/web/src/components/search/AddressSearch.tsx`)

```typescript
"use client";

import { useState, useCallback } from "react";
import { useRouter } from "next/navigation";
import { apiFetch } from "@/lib/api";
import type { LookupResponse } from "@/types/api";

export default function AddressSearch() {
  const router = useRouter();
  const [address, setAddress] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const handleSearch = useCallback(async () => {
    if (!address.trim()) return;
    setLoading(true);
    setError(null);

    try {
      const result = await apiFetch<LookupResponse>(
        `/api/v1/lookup?address=${encodeURIComponent(address)}`
      );
      router.push(`/report/${result.address_id}`);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Something went wrong");
    } finally {
      setLoading(false);
    }
  }, [address, router]);

  return (
    <div className="space-y-3">
      <div className="flex gap-2">
        <input
          type="text"
          value={address}
          onChange={(e) => setAddress(e.target.value)}
          onKeyDown={(e) => e.key === "Enter" && handleSearch()}
          placeholder="Enter any U.S. address..."
          className="flex-1 bg-slate-800 border border-slate-700 rounded-xl px-4 py-3
                     text-white placeholder-slate-500 text-lg
                     focus:outline-none focus:ring-2 focus:ring-blue-500"
        />
        <button
          onClick={handleSearch}
          disabled={loading || !address.trim()}
          className="bg-blue-600 hover:bg-blue-500 disabled:bg-slate-700
                     text-white font-semibold px-6 py-3 rounded-xl
                     transition-colors duration-150 whitespace-nowrap"
        >
          {loading ? "Searching..." : "Analyze"}
        </button>
      </div>
      {error && (
        <p className="text-red-400 text-sm">{error}</p>
      )}
    </div>
  );
}
```

---

## Step 6: Score Ring Component (`apps/web/src/components/ui/ScoreRing.tsx`)

SVG circular progress indicator used throughout the report.

```typescript
interface ScoreRingProps {
  score: number;      // 0-100
  size?: number;
  strokeWidth?: number;
  label?: string;
}

export default function ScoreRing({
  score,
  size = 120,
  strokeWidth = 8,
  label,
}: ScoreRingProps) {
  const radius = (size - strokeWidth) / 2;
  const circumference = 2 * Math.PI * radius;
  const offset = circumference - (score / 100) * circumference;

  const color =
    score >= 75 ? "#22c55e" :
    score >= 50 ? "#eab308" :
    "#ef4444";

  return (
    <div className="flex flex-col items-center gap-2">
      <svg width={size} height={size} className="-rotate-90">
        <circle
          cx={size / 2}
          cy={size / 2}
          r={radius}
          fill="none"
          stroke="#1e293b"
          strokeWidth={strokeWidth}
        />
        <circle
          cx={size / 2}
          cy={size / 2}
          r={radius}
          fill="none"
          stroke={color}
          strokeWidth={strokeWidth}
          strokeDasharray={circumference}
          strokeDashoffset={offset}
          strokeLinecap="round"
          style={{ transition: "stroke-dashoffset 0.8s ease" }}
        />
      </svg>
      <div className="absolute text-2xl font-bold text-white -mt-1">
        {Math.round(score)}
      </div>
      {label && (
        <span className="text-sm text-slate-400">{label}</span>
      )}
    </div>
  );
}
```

---

## Step 7: Report Page (`apps/web/src/app/report/[addressId]/page.tsx`)

```typescript
import { apiFetch } from "@/lib/api";
import ScoreSummary from "@/components/report/ScoreSummary";
import NarrativePanel from "@/components/report/NarrativePanel";
import ScoreBreakdown from "@/components/report/ScoreBreakdown";
import MapView from "@/components/report/MapView";
import type { NeighborhoodReport } from "@/types/api";

interface Props {
  params: { addressId: string };
}

export default async function ReportPage({ params }: Props) {
  // Server Component — fetch on the server for SEO + no loading flicker
  const report = await apiFetch<NeighborhoodReport>(
    `/api/v1/score/${params.addressId}`
  );

  return (
    <div className="min-h-screen bg-slate-950 text-white">
      <div className="max-w-5xl mx-auto px-4 py-12 space-y-10">
        <header>
          <h1 className="text-3xl font-bold">{report.address_normalized}</h1>
          <p className="text-slate-400 mt-1">Census tract {report.geoid}</p>
        </header>

        <ScoreSummary report={report} />
        <MapView lat={report.latitude} lng={report.longitude} />
        <NarrativePanel narrative={report.narrative} />
        <ScoreBreakdown report={report} />
      </div>
    </div>
  );
}
```

---

## Step 8: Utility Functions (`apps/web/src/lib/utils.ts`)

```typescript
import { clsx, type ClassValue } from "clsx";
import { twMerge } from "tailwind-merge";

/** Merges Tailwind classes safely */
export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs));
}

/** Returns a color class based on score value */
export function scoreColor(score: number): string {
  if (score >= 75) return "text-green-400";
  if (score >= 50) return "text-yellow-400";
  return "text-red-400";
}

/** Returns a letter grade A–F from a 0–100 score */
export function scoreGrade(score: number): string {
  if (score >= 90) return "A+";
  if (score >= 80) return "A";
  if (score >= 70) return "B";
  if (score >= 60) return "C";
  if (score >= 50) return "D";
  return "F";
}
```

---

## Step 9: Auth Setup (`apps/web/src/lib/auth.ts`)

```typescript
import NextAuth from "next-auth";
import Credentials from "next-auth/providers/credentials";
import { apiFetch } from "./api";

export const { handlers, signIn, signOut, auth } = NextAuth({
  providers: [
    Credentials({
      credentials: {
        email: { label: "Email", type: "email" },
        password: { label: "Password", type: "password" },
      },
      async authorize(credentials) {
        try {
          const response = await apiFetch<{ access_token: string; user: { id: string; email: string; full_name: string } }>(
            "/api/v1/auth/login",
            {
              method: "POST",
              body: JSON.stringify(credentials),
            }
          );
          return {
            id: response.user.id,
            email: response.user.email,
            name: response.user.full_name,
            accessToken: response.access_token,
          };
        } catch {
          return null;
        }
      },
    }),
  ],
  callbacks: {
    async jwt({ token, user }) {
      if (user) token.accessToken = (user as any).accessToken;
      return token;
    },
    async session({ session, token }) {
      (session as any).accessToken = token.accessToken;
      return session;
    },
  },
  pages: {
    signIn: "/login",
  },
});
```

Create `apps/web/src/app/api/auth/[...nextauth]/route.ts`:

```typescript
import { handlers } from "@/lib/auth";
export const { GET, POST } = handlers;
```

---

## Step 10: Freemium Gate (`apps/web/src/components/paywall/UpgradePrompt.tsx`)

```typescript
"use client";

import { useRouter } from "next/navigation";

interface Props {
  feature: string;
  tier: "buyer" | "buyer_pro";
}

const tierLabels = {
  buyer: "Buyer ($19/mo)",
  buyer_pro: "Buyer Pro ($49/mo)",
};

export default function UpgradePrompt({ feature, tier }: Props) {
  const router = useRouter();

  return (
    <div className="border border-slate-700 rounded-xl p-6 text-center space-y-4
                    bg-slate-900/50 backdrop-blur-sm">
      <div className="text-2xl">🔒</div>
      <p className="text-slate-300 font-medium">{feature} is a {tierLabels[tier]} feature</p>
      <button
        onClick={() => router.push("/pricing")}
        className="bg-blue-600 hover:bg-blue-500 text-white font-semibold
                   px-6 py-2 rounded-lg transition-colors"
      >
        Upgrade to Unlock
      </button>
    </div>
  );
}
```

---

## Tailwind Config (`apps/web/tailwind.config.ts`)

```typescript
import type { Config } from "tailwindcss";

const config: Config = {
  content: ["./src/**/*.{ts,tsx}"],
  theme: {
    extend: {
      colors: {
        brand: {
          DEFAULT: "#3b82f6",
          dark: "#1d4ed8",
        },
      },
      fontFamily: {
        sans: ["var(--font-inter)", "sans-serif"],
        mono: ["var(--font-mono)", "monospace"],
      },
    },
  },
  plugins: [],
};

export default config;
```

---

## Checklist

- [ ] All directories and files created
- [ ] `npm run dev` starts without errors at `localhost:3000`
- [ ] Address search form renders on homepage
- [ ] `/report/[addressId]` route renders (can use mock data initially)
- [ ] Auth.js login/register pages render
- [ ] No TypeScript errors (`npm run build`)
- [ ] All API calls go through `apiFetch` — no raw `fetch` in components
