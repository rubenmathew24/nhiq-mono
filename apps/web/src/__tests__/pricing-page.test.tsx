import { describe, it, expect } from "vitest";
import { pricingTiers } from "@/content/landing";

// Lightweight smoke test — pricing tiers from shared content appear on screen.
// Full page test would require server component rendering setup.
describe("pricingTiers content", () => {
  it("exports all three base tiers", () => {
    const names = pricingTiers.map((t) => t.name);
    expect(names).toContain("Free");
    expect(names).toContain("Buyer");
    expect(names).toContain("Buyer Pro");
  });

  it("Buyer tier is highlighted (most popular)", () => {
    const buyer = pricingTiers.find((t) => t.name === "Buyer");
    expect(buyer?.highlighted).toBe(true);
  });

  it("all tiers have a cta string", () => {
    pricingTiers.forEach((tier) => {
      expect(typeof tier.cta).toBe("string");
      expect(tier.cta.length).toBeGreaterThan(0);
    });
  });
});
