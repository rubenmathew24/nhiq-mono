import { describe, it, expect } from "vitest";
import { render, screen } from "@testing-library/react";
import PricingTiersGrid, {
  formatTierLabel,
  resolveSessionTier,
} from "@/components/pricing/PricingTiersGrid";

describe("PricingTiersGrid", () => {
  it("guest mode links CTAs to register", () => {
    render(<PricingTiersGrid mode="guest" />);
    const links = screen.getAllByRole("link");
    expect(links.length).toBeGreaterThan(0);
    links.forEach((link) => {
      expect(link).toHaveAttribute("href", "/register");
    });
    expect(screen.queryByText(/current plan/i)).not.toBeInTheDocument();
    expect(screen.queryByText(/coming soon/i)).not.toBeInTheDocument();
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
