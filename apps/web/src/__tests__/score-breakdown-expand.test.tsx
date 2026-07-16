import { fireEvent, render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import ScoreBreakdown from "@/components/report/ScoreBreakdown";
import type { NeighborhoodReport, ScoreDimension } from "@/types/api";

function dim(
  score: number,
  overrides: Partial<ScoreDimension> = {},
): ScoreDimension {
  return {
    score,
    label: "X",
    summary: "Summary text",
    factors: [
      { name: "Nearest ER", value: "Mercy · 2.1 mi · ★4", impact: "positive" },
    ],
    sub_scores: [
      { id: "access", label: "Access", score: 90, available: true },
      { id: "quality", label: "Quality", score: 80, available: true },
    ],
    ...overrides,
  };
}

const report: NeighborhoodReport = {
  address: "1 Main",
  address_normalized: "1 Main",
  geoid: "05007020101",
  latitude: 36,
  longitude: -94,
  overall_score: 80,
  healthcare: dim(87),
  safety: dim(74, { factors: [{ name: "Crime", value: "Near average", impact: "neutral" }] }),
  environment: dim(74),
  education: dim(91),
  economic: dim(68),
  narrative: "n",
  data_vintage: "2026-Q3",
  computed_at: new Date().toISOString(),
};

describe("ScoreBreakdown expand", () => {
  it("shows sub-scores and expand affordance", () => {
    render(<ScoreBreakdown report={report} />);
    expect(screen.getByText("Access")).toBeInTheDocument();
    expect(screen.getAllByText(/View details/).length).toBeGreaterThanOrEqual(1);
    expect(
      screen.getByRole("button", { name: /Expand Healthcare details/i }),
    ).toBeInTheDocument();
  });

  it("expands and collapses healthcare stats", () => {
    render(<ScoreBreakdown report={report} />);
    const btn = screen.getByRole("button", { name: /Expand Healthcare details/i });
    expect(screen.queryByText(/Mercy/)).not.toBeInTheDocument();
    fireEvent.click(btn);
    expect(screen.getByText(/Mercy/)).toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: /Collapse Healthcare details/i }));
    expect(screen.queryByText(/Mercy/)).not.toBeInTheDocument();
  });
});
