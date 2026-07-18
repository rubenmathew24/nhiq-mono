"use client";

import { useMemo, useState } from "react";
import type { SourceCoverage, StateCoverage } from "@/types/api";

type Tab = "overall" | "source" | "state";

export default function CoverageViews({
  sources,
  states,
  labelJob,
}: {
  sources: SourceCoverage[];
  states: StateCoverage[];
  labelJob: (name: string) => string;
}) {
  const [tab, setTab] = useState<Tab>("overall");
  const [selectedJob, setSelectedJob] = useState(sources[0]?.job_name ?? "scoring");

  const stateRows = useMemo(() => {
    return [...states].sort((a, b) => a.state_abbr.localeCompare(b.state_abbr));
  }, [states]);

  const tabs: { id: Tab; label: string }[] = [
    { id: "overall", label: "Overall" },
    { id: "source", label: "By source" },
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

      {tab === "overall" && (
        <SourceTable sources={sources} labelJob={labelJob} />
      )}

      {tab === "source" && (
        <div className="space-y-4">
          <label className="block text-sm font-medium">
            Source
            <select
              className="mt-1 block w-full max-w-sm rounded-md border border-border bg-background px-3 py-2 text-sm"
              value={selectedJob}
              onChange={(e) => setSelectedJob(e.target.value)}
            >
              {sources.map((s) => (
                <option key={s.job_name} value={s.job_name}>
                  {labelJob(s.job_name)}
                </option>
              ))}
            </select>
          </label>
          {(() => {
            const src = sources.find((s) => s.job_name === selectedJob);
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
          })()}
          <StateTableForJob
            states={stateRows}
            jobName={selectedJob}
            labelJob={labelJob}
          />
        </div>
      )}

      {tab === "state" && (
        <div className="overflow-x-auto rounded-xl border border-border">
          <table className="w-full min-w-[640px] text-left text-sm">
            <thead className="border-b border-border bg-muted/30 text-xs uppercase tracking-wide text-muted-foreground">
              <tr>
                <th className="px-4 py-3 font-medium">State</th>
                <th className="px-4 py-3 font-medium">Counties</th>
                <th className="px-4 py-3 font-medium">Mean %</th>
                <th className="px-4 py-3 font-medium">Scoring</th>
              </tr>
            </thead>
            <tbody>
              {stateRows.map((st) => {
                const mean =
                  st.sources.length === 0
                    ? 0
                    : st.sources.reduce((a, s) => a + s.pct_complete, 0) /
                      st.sources.length;
                const scoring = st.sources.find((s) => s.job_name === "scoring");
                return (
                  <tr key={st.state_fips} className="border-b border-border/60">
                    <td className="px-4 py-2.5 font-medium">{st.state_abbr}</td>
                    <td className="px-4 py-2.5 tabular-nums">{st.county_total}</td>
                    <td className="px-4 py-2.5 tabular-nums">{mean.toFixed(1)}%</td>
                    <td className="px-4 py-2.5 tabular-nums">
                      {scoring
                        ? `${scoring.pct_complete.toFixed(1)}% (${scoring.done_count}/${scoring.total_count})`
                        : "—"}
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}

function SourceTable({
  sources,
  labelJob,
}: {
  sources: SourceCoverage[];
  labelJob: (name: string) => string;
}) {
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

function StateTableForJob({
  states,
  jobName,
  labelJob,
}: {
  states: StateCoverage[];
  jobName: string;
  labelJob: (name: string) => string;
}) {
  return (
    <div className="overflow-x-auto rounded-xl border border-border">
      <table className="w-full min-w-[480px] text-left text-sm">
        <thead className="border-b border-border bg-muted/30 text-xs uppercase tracking-wide text-muted-foreground">
          <tr>
            <th className="px-4 py-3 font-medium">State</th>
            <th className="px-4 py-3 font-medium">
              {labelJob(jobName)} done / total
            </th>
            <th className="px-4 py-3 font-medium">%</th>
          </tr>
        </thead>
        <tbody>
          {states.map((st) => {
            const src = st.sources.find((s) => s.job_name === jobName);
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
