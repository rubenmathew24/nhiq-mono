import { describe, it, expect } from "vitest";
import { render, screen } from "@testing-library/react";
import ReportAiSummary from "@/components/report/ReportAiSummary";

describe("ReportAiSummary", () => {
  it("shows live narrative without sample-score framing", () => {
    render(
      <ReportAiSummary narrative="Overall score 90.4 (2026-Q3). Safety 99.2 (fbi_cde)." />,
    );
    expect(screen.getByText(/Overall score 90\.4/)).toBeInTheDocument();
    expect(screen.queryByText(/Sample scores/i)).not.toBeInTheDocument();
    expect(screen.getByText(/Deterministic preview from live scores/i)).toBeInTheDocument();
  });
});
