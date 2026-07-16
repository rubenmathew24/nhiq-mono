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
    summary: "Strong access to nearby emergency care for this area.",
  }),
  safety: dim(74, {
    factors: [{ name: "Assault", value: "20 incidents (12 mo)", impact: "neutral" }],
  }),
  environment: dim(74, {
    summary:
      "Strong air quality from modeled US AQI (EPA monitors unavailable or too sparse for this county).",
  }),
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
    expect(
      container.querySelectorAll('[data-category-box].rounded-xl.border').length,
    ).toBeGreaterThanOrEqual(5);
    const btn = screen.getByRole("button", { name: /Expand Healthcare details/i });
    expect(btn.className).toMatch(/hover:bg-muted\/55/);
  });

  it("expands when clicking sub-score area (full box)", () => {
    render(<ScoreBreakdown report={report} />);
    expect(screen.queryByText(/162 min/)).not.toBeInTheDocument();
    fireEvent.click(screen.getAllByText("Access")[0]);
    expect(screen.getByText(/162 min/)).toBeInTheDocument();
  });

  it("expands when clicking category summary text", () => {
    render(<ScoreBreakdown report={report} />);
    expect(screen.queryByText(/162 min/)).not.toBeInTheDocument();
    fireEvent.click(
      screen.getByText(/Strong access to nearby emergency care/i),
    );
    expect(screen.getByText(/162 min/)).toBeInTheDocument();
  });

  it("does not expand when pointer is dragged (text selection gesture)", () => {
    render(<ScoreBreakdown report={report} />);
    const box = screen.getByRole("button", { name: /Expand Healthcare details/i });
    fireEvent.pointerDown(box, { clientX: 10, clientY: 10 });
    fireEvent.click(box, { clientX: 40, clientY: 10 });
    expect(screen.queryByText(/162 min/)).not.toBeInTheDocument();
  });

  it("expands and collapses healthcare stats", () => {
    render(<ScoreBreakdown report={report} />);
    const btn = screen.getByRole("button", { name: /Expand Healthcare details/i });
    expect(screen.queryByText(/162 min/)).not.toBeInTheDocument();
    fireEvent.click(btn);
    expect(screen.getByText(/162 min/)).toBeInTheDocument();
    const waitValue = screen.getByText(/162 min/);
    expect(waitValue.className).toMatch(/score-poor|text-score-poor/);
    fireEvent.click(screen.getByRole("button", { name: /Collapse Healthcare details/i }));
    expect(screen.queryByText(/162 min/)).not.toBeInTheDocument();
  });

  it("collapses when clicking expand-panel value (panel chrome is activatable)", () => {
    render(<ScoreBreakdown report={report} />);
    fireEvent.click(
      screen.getByRole("button", { name: /Expand Healthcare details/i }),
    );
    const waitValue = screen.getByText(/162 min/);
    expect(waitValue).toBeInTheDocument();
    fireEvent.click(waitValue);
    expect(screen.queryByText(/162 min/)).not.toBeInTheDocument();
  });
});
