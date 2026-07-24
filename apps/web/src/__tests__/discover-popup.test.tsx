import { describe, it, expect } from "vitest";
import { popupCopy } from "@/lib/discoverPopup";

describe("discover popup copy", () => {
  it("formats scored and unscored without report links", () => {
    const scored = popupCopy("25025000100", 72.5);
    expect(scored).toContain("72.5");
    expect(scored.toLowerCase()).not.toContain("/report");
    expect(scored).toContain("25025000100");

    const missing = popupCopy("25025000200", null);
    expect(missing.toLowerCase()).toContain("unavailable");
    expect(missing.toLowerCase()).not.toContain("/report");
  });
});
