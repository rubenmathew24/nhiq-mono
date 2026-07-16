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
      {
        name: "Nearest ER",
        value: "Mercy · 2.1 mi · ★4",
        impact: "positive",
        tone_score: 90,
      },
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
  healthcare: dim(87, {
    factors: [
      {
        name: "ER wait",
        value: "162 min (national 161)",
        impact: "negative",
        tone_score: 49,
      },
    ],
  }),
  safety: dim(74, {
    factors: [{ name: "Assault", value: "20 incidents (12 mo)", impact: "neutral" }],
  }),
  environment: dim(74),
  education: dim(91),
  economic: dim(68),
  narrative: "n",
  data_vintage: "2026-Q3",
  computed_at: new Date().toISOString(),
};

describe("ScoreBreakdown expand", () => {
  it("shows sub-scores and interactive category boxes without View details", () => {
    const { container } = render(<ScoreBreakdown report={report} />);
    expect(screen.getAllByText("Access").length).toBeGreaterThanOrEqual(1);
    expect(screen.queryByText(/View details/i)).not.toBeInTheDocument();
    expect(
      screen.getByRole("button", { name: /Expand Healthcare details/i }),
    ).toBeInTheDocument();
    // Category boxes use bordered surfaces
    expect(container.querySelectorAll(".rounded-xl.border").length).toBeGreaterThanOrEqual(5);
  });

  it("expands and collapses healthcare stats", () => {
    render(<ScoreBreakdown report={report} />);
    const btn = screen.getByRole("button", { name: /Expand Healthcare details/i });
    expect(screen.queryByText(/162 min/)).not.toBeInTheDocument();
    fireEvent.click(btn);
    expect(screen.getByText(/162 min/)).toBeInTheDocument();
    // tone_score < 50 → score-poor text class
    const waitValue = screen.getByText(/162 min/);
    expect(waitValue.className).toMatch(/score-poor|text-score-poor/);
    fireEvent.click(screen.getByRole("button", { name: /Collapse Healthcare details/i }));
    expect(screen.queryByText(/162 min/)).not.toBeInTheDocument();
  });
});
