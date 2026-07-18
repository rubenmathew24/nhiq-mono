"use client";

import { useMemo, useState } from "react";
import type { SourceCoverage, StateCoverage } from "@/types/api";

type Tab = "overall" | "state";

const OVERALL_FILTER = "overall";

const JOB_LABELS: Record<string, string> = {
  [OVERALL_FILTER]: "Overall",
  census: "Census tracts",
  epa: "Air quality (EPA)",
  cms: "Hospitals (CMS)",
  fbi: "Crime (FBI)",
  nces: "Schools (NCES)",
  urban: "Schools (Urban)",
  acs: "ACS indicators",
  bls: "Unemployment (BLS)",
  fema: "Hazards (FEMA NRI)",
  cms_timely: "Timely care (CMS)",
  scoring: "Neighborhood scores",
};

function labelJob(name: string): string {
  return JOB_LABELS[name] ?? name;
}

function meanPct(sources: SourceCoverage[]): number {
  if (sources.length === 0) return 0;
  return sources.reduce((a, s) => a + s.pct_complete, 0) / sources.length;
}

export default function CoverageViews({
  sources,
  states,
  overallPct,
}: {
  sources: SourceCoverage[];
  states: StateCoverage[];
  overallPct: number;
}) {
  const [tab, setTab] = useState<Tab>("overall");
  const [selectedFilter, setSelectedFilter] = useState(OVERALL_FILTER);

  const stateRows = useMemo(() => {
    return [...states].sort((a, b) => a.state_abbr.localeCompare(b.state_abbr));
  }, [states]);

  const filterOptions = useMemo(
    () => [OVERALL_FILTER, ...sources.map((s) => s.job_name)],
    [sources],
  );

  const tabs: { id: Tab; label: string }[] = [
    { id: "overall", label: "Overall" },
    { id: "state", label: "By state" },
  ];

  return (
    <div className="space-y-6">
      <div
        className="flex flex-wrap gap-2 border-b border-border pb-3"
        role="tablist"
        aria-label="Coverage views"
      >
        {tabs.map((t) => (
          <button
            key={t.id}
            type="button"
            role="tab"
            aria-selected={tab === t.id}
            onClick={() => setTab(t.id)}
            className={
              tab === t.id
                ? "rounded-md bg-primary px-3 py-1.5 text-sm font-semibold text-primary-foreground"
                : "rounded-md px-3 py-1.5 text-sm font-medium text-muted-foreground hover:text-foreground"
            }
          >
            {t.label}
          </button>
        ))}
      </div>

      {tab === "overall" && <SourceTable sources={sources} />}

      {tab === "state" && (
        <div className="space-y-4">
          <label className="block text-sm font-medium">
            Source
            <select
              className="mt-1 block w-full max-w-sm rounded-md border border-border bg-background px-3 py-2 text-sm"
              value={selectedFilter}
              onChange={(e) => setSelectedFilter(e.target.value)}
            >
              {filterOptions.map((name) => (
                <option key={name} value={name}>
                  {labelJob(name)}
                </option>
              ))}
            </select>
          </label>
          <StateFilterSummary
            filter={selectedFilter}
            sources={sources}
            overallPct={overallPct}
          />
          <StateTableForFilter
            states={stateRows}
            filter={selectedFilter}
          />
        </div>
      )}
    </div>
  );
}

function StateFilterSummary({
  filter,
  sources,
  overallPct,
}: {
  filter: string;
  sources: SourceCoverage[];
  overallPct: number;
}) {
  if (filter === OVERALL_FILTER) {
    return (
      <div className="rounded-xl border border-border px-5 py-4 space-y-2">
        <p className="font-display text-2xl font-bold tabular-nums">
          {overallPct.toFixed(1)}%
        </p>
        <p className="text-sm text-muted-foreground">
          Mean of all sources (national)
        </p>
        <ProgressBar pct={overallPct} />
      </div>
    );
  }

  const src = sources.find((s) => s.job_name === filter);
  if (!src) return null;

  return (
    <div className="rounded-xl border border-border px-5 py-4 space-y-2">
      <p className="font-display text-2xl font-bold tabular-nums">
        {src.pct_complete.toFixed(1)}%
      </p>
      <p className="text-sm text-muted-foreground">
        {src.done_count.toLocaleString()} / {src.total_count.toLocaleString()}{" "}
        ({src.grain}-grain)
      </p>
      <ProgressBar pct={src.pct_complete} />
    </div>
  );
}

function SourceTable({ sources }: { sources: SourceCoverage[] }) {
  return (
    <div className="overflow-x-auto rounded-xl border border-border">
      <table className="w-full min-w-[560px] text-left text-sm">
        <thead className="border-b border-border bg-muted/30 text-xs uppercase tracking-wide text-muted-foreground">
          <tr>
            <th className="px-4 py-3 font-medium">Source</th>
            <th className="px-4 py-3 font-medium">Grain</th>
            <th className="px-4 py-3 font-medium">Done</th>
            <th className="px-4 py-3 font-medium">Total</th>
            <th className="px-4 py-3 font-medium">%</th>
          </tr>
        </thead>
        <tbody>
          {sources.map((s) => (
            <tr key={s.job_name} className="border-b border-border/60">
              <td className="px-4 py-2.5 font-medium">{labelJob(s.job_name)}</td>
              <td className="px-4 py-2.5 text-muted-foreground">{s.grain}</td>
              <td className="px-4 py-2.5 tabular-nums">
                {s.done_count.toLocaleString()}
              </td>
              <td className="px-4 py-2.5 tabular-nums">
                {s.total_count.toLocaleString()}
              </td>
              <td className="px-4 py-2.5">
                <div className="flex items-center gap-2">
                  <span className="tabular-nums w-14">
                    {s.pct_complete.toFixed(1)}%
                  </span>
                  <div className="flex-1 max-w-[120px]">
                    <ProgressBar pct={s.pct_complete} />
                  </div>
                </div>
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

function StateTableForFilter({
  states,
  filter,
}: {
  states: StateCoverage[];
  filter: string;
}) {
  const isOverall = filter === OVERALL_FILTER;

  return (
    <div className="overflow-x-auto rounded-xl border border-border">
      <table className="w-full min-w-[480px] text-left text-sm">
        <thead className="border-b border-border bg-muted/30 text-xs uppercase tracking-wide text-muted-foreground">
          <tr>
            <th className="px-4 py-3 font-medium">State</th>
            {!isOverall && (
              <th className="px-4 py-3 font-medium">
                {labelJob(filter)} done / total
              </th>
            )}
            <th className="px-4 py-3 font-medium">
              {isOverall ? "Mean %" : "%"}
            </th>
          </tr>
        </thead>
        <tbody>
          {states.map((st) => {
            if (isOverall) {
              const pct = meanPct(st.sources);
              return (
                <tr key={st.state_fips} className="border-b border-border/60">
                  <td className="px-4 py-2.5 font-medium">{st.state_abbr}</td>
                  <td className="px-4 py-2.5 tabular-nums">{pct.toFixed(1)}%</td>
                </tr>
              );
            }

            const src = st.sources.find((s) => s.job_name === filter);
            if (!src) return null;
            return (
              <tr key={st.state_fips} className="border-b border-border/60">
                <td className="px-4 py-2.5 font-medium">{st.state_abbr}</td>
                <td className="px-4 py-2.5 tabular-nums">
                  {src.done_count.toLocaleString()} /{" "}
                  {src.total_count.toLocaleString()}
                </td>
                <td className="px-4 py-2.5 tabular-nums">
                  {src.pct_complete.toFixed(1)}%
                </td>
              </tr>
            );
          })}
        </tbody>
      </table>
    </div>
  );
}

function ProgressBar({ pct }: { pct: number }) {
  const clamped = Math.max(0, Math.min(100, pct));
  return (
    <div
      className="h-1.5 w-full rounded-full bg-muted overflow-hidden"
      aria-hidden="true"
    >
      <div
        className="h-full rounded-full bg-mint"
        style={{ width: `${clamped}%` }}
      />
    </div>
  );
}
