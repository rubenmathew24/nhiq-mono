import { describe, it, expect } from "vitest";
import {
  relativeScoreColor,
  scoreRange,
  UNSCORED_TRACT_COLOR,
  buildFillColorExpression,
} from "@/lib/discoverColors";

describe("discoverColors", () => {
  it("returns null range when no scores", () => {
    expect(scoreRange([null, undefined])).toBeNull();
  });

  it("computes min/max", () => {
    expect(scoreRange([10, 90, null, 50])).toEqual({ min: 10, max: 90 });
  });

  it("uses gray for null scores", () => {
    expect(relativeScoreColor(null, 0, 100)).toBe(UNSCORED_TRACT_COLOR);
  });

  it("maps mid when min===max", () => {
    const c = relativeScoreColor(70, 70, 70);
    expect(c).toMatch(/^rgb\(/);
    expect(c).not.toBe(UNSCORED_TRACT_COLOR);
  });

  it("builds match expression with geoids", () => {
    const expr = buildFillColorExpression([
      { properties: { geoid: "a", overall_score: 10 } },
      { properties: { geoid: "b", overall_score: 90 } },
      { properties: { geoid: "c", overall_score: null } },
    ]);
    expect(expr[0]).toBe("match");
    expect(expr).toContain("a");
    expect(expr).toContain("b");
    expect(expr[expr.length - 1]).toBe(UNSCORED_TRACT_COLOR);
  });
});
