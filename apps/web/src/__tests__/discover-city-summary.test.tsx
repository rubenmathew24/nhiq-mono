import { describe, it, expect, vi } from "vitest";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import DiscoverCitySummary from "@/components/discover/DiscoverCitySummary";
import type { DiscoverSummary } from "@/types/discover";

const fullSummary: DiscoverSummary = {
  scope_mode: "inner_bbox",
  average_overall: 72.6,
  score_min: 54.2,
  score_max: 91.0,
  scored_count: 2,
  total_count: 2,
  highest: {
    geoid: "05007020102",
    overall_score: 91.0,
    label: "Bentonville · Tract 020102",
  },
  lowest: {
    geoid: "05007020101",
    overall_score: 54.2,
    label: "Bentonville · Tract 020101",
  },
  insufficient_data: false,
};

describe("DiscoverCitySummary", () => {
  it("orders headline then highest then lowest", () => {
    render(
      <DiscoverCitySummary
        summary={fullSummary}
        focusedGeoid={null}
        onFocusGeoid={() => {}}
      />,
    );
    const section = screen.getByLabelText(/city score snapshot/i);
    const text = section.textContent ?? "";
    const avgIdx = text.indexOf("Average overall");
    const highIdx = text.indexOf("Highest");
    const lowIdx = text.indexOf("Lowest");
    expect(avgIdx).toBeGreaterThanOrEqual(0);
    expect(highIdx).toBeGreaterThan(avgIdx);
    expect(lowIdx).toBeGreaterThan(highIdx);
    expect(screen.getByText(/Bentonville · Tract 020102/)).toBeInTheDocument();
    expect(screen.getByText(/GEOID 05007020102/)).toBeInTheDocument();
  });

  it("shows insufficient state without fake high/low", () => {
    const empty: DiscoverSummary = {
      ...fullSummary,
      highest: null,
      lowest: null,
      insufficient_data: true,
      scored_count: 1,
    };
    render(
      <DiscoverCitySummary
        summary={empty}
        focusedGeoid={null}
        onFocusGeoid={() => {}}
      />,
    );
    expect(
      screen.getByText(/not enough scored neighborhoods/i),
    ).toBeInTheDocument();
    expect(screen.queryByText(/^Highest$/i)).not.toBeInTheDocument();
  });
});

describe("DiscoverCitySummary focus handlers", () => {
  it("hover does not change map focus", async () => {
    const user = userEvent.setup();
    const onFocus = vi.fn();
    render(
      <DiscoverCitySummary
        summary={fullSummary}
        focusedGeoid={null}
        onFocusGeoid={onFocus}
      />,
    );
    const highest = screen.getByRole("button", { name: /highest/i });
    const lowest = screen.getByRole("button", { name: /lowest/i });
    await user.hover(highest);
    await user.hover(lowest);
    expect(onFocus).not.toHaveBeenCalled();
  });

  it("click toggles focus and shows clear hint; switch rows without null gap", async () => {
    const user = userEvent.setup();
    const onFocus = vi.fn();
    const { rerender } = render(
      <DiscoverCitySummary
        summary={fullSummary}
        focusedGeoid={null}
        onFocusGeoid={onFocus}
      />,
    );
    const highest = screen.getByRole("button", { name: /highest/i });
    await user.click(highest);
    expect(onFocus).toHaveBeenCalledWith("05007020102");
    expect(screen.queryByRole("link", { name: /report/i })).toBeNull();

    rerender(
      <DiscoverCitySummary
        summary={fullSummary}
        focusedGeoid="05007020102"
        onFocusGeoid={onFocus}
      />,
    );
    expect(screen.getByText(/Focused · click to clear/i)).toBeInTheDocument();

    onFocus.mockClear();
    await user.click(screen.getByRole("button", { name: /lowest/i }));
    expect(onFocus).toHaveBeenCalledWith("05007020101");
    expect(onFocus).not.toHaveBeenCalledWith(null);

    rerender(
      <DiscoverCitySummary
        summary={fullSummary}
        focusedGeoid="05007020101"
        onFocusGeoid={onFocus}
      />,
    );
    onFocus.mockClear();
    await user.click(screen.getByRole("button", { name: /lowest/i }));
    expect(onFocus).toHaveBeenCalledWith(null);
  });
});
