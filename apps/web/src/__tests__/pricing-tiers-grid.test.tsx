import { describe, it, expect } from "vitest";
import { render, screen } from "@testing-library/react";
import PricingTiersGrid, {
  formatTierLabel,
  resolveSessionTier,
} from "@/components/pricing/PricingTiersGrid";

describe("PricingTiersGrid", () => {
  it("guest mode only Free links to register; paid tiers are coming soon", () => {
    render(<PricingTiersGrid mode="guest" />);
    const links = screen.getAllByRole("link");
    expect(links).toHaveLength(1);
    expect(links[0]).toHaveAttribute("href", "/register");
    expect(links[0]).toHaveAccessibleName(/start free/i);
    expect(screen.getAllByRole("button", { name: /coming soon/i })).toHaveLength(2);
    expect(screen.queryByText(/current plan/i)).not.toBeInTheDocument();
  });

  it("upgrade mode labels current plan and disables other CTAs", () => {
    render(<PricingTiersGrid mode="upgrade" currentTier="free" />);
    expect(screen.getAllByText(/current plan/i).length).toBeGreaterThanOrEqual(1);
    expect(screen.getAllByRole("button", { name: /coming soon/i }).length).toBeGreaterThanOrEqual(1);
    expect(screen.queryByRole("link", { name: /get started|start free|upgrade/i })).not.toBeInTheDocument();
  });

  it("formatTierLabel and resolveSessionTier map session values", () => {
    expect(formatTierLabel("buyer_pro")).toBe("Buyer Pro");
    expect(resolveSessionTier({ user: { tier: "buyer" } })).toBe("buyer");
    expect(resolveSessionTier(null)).toBe("free");
  });
});
