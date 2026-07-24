/**
 * Focus wiring is covered alongside DiscoverCitySummary in
 * discover-city-summary.test.tsx (hover/tap set/clear focusedGeoid).
 * This file keeps a dedicated US4 focus contract for the task checklist.
 */
import { describe, it, expect, vi } from "vitest";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import DiscoverCitySummary from "@/components/discover/DiscoverCitySummary";
import type { DiscoverSummary } from "@/types/discover";

const summary: DiscoverSummary = {
  scope_mode: "inner_bbox",
  average_overall: 70,
  score_min: 40,
  score_max: 90,
  scored_count: 2,
  total_count: 2,
  highest: {
    geoid: "111",
    overall_score: 90,
    label: "Demo · Tract 111",
  },
  lowest: {
    geoid: "222",
    overall_score: 40,
    label: "Demo · Tract 222",
  },
  insufficient_data: false,
};

describe("discover summary focus", () => {
  it("does not navigate to report routes on focus", async () => {
    const user = userEvent.setup();
    const onFocus = vi.fn();
    render(
      <DiscoverCitySummary
        summary={summary}
        focusedGeoid={null}
        onFocusGeoid={onFocus}
      />,
    );
    await user.click(screen.getByRole("button", { name: /lowest/i }));
    expect(onFocus).toHaveBeenCalledWith("222");
    expect(document.querySelector('a[href*="/report"]')).toBeNull();
  });
});
