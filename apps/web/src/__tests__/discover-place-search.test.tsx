import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import { render, screen, fireEvent, waitFor } from "@testing-library/react";
import DiscoverPlaceSearch from "@/components/discover/DiscoverPlaceSearch";
import { navLinks } from "@/content/landing";
import { buildDiscoverMapHref } from "@/types/discover";

const push = vi.fn();

vi.mock("next/navigation", () => ({
  useRouter: () => ({ push }),
}));

describe("Discover nav", () => {
  it("includes Discover in navLinks", () => {
    expect(navLinks.some((l) => l.href === "/discover" && l.label === "Discover")).toBe(
      true,
    );
  });
});

describe("buildDiscoverMapHref", () => {
  it("encodes place and bbox", () => {
    const href = buildDiscoverMapHref({
      place: "Boston, Massachusetts, United States",
      min_lng: -71.2,
      min_lat: 42.2,
      max_lng: -70.9,
      max_lat: 42.4,
    });
    expect(href.startsWith("/discover/map?")).toBe(true);
    expect(href).toContain("min_lng=-71.2");
    expect(href).toContain("place=Boston");
  });
});

describe("DiscoverPlaceSearch", () => {
  beforeEach(() => {
    push.mockClear();
    vi.stubEnv("NEXT_PUBLIC_MAPBOX_TOKEN", "pk.test");
    globalThis.fetch = vi.fn().mockResolvedValue(
      new Response(
        JSON.stringify({
          features: [
            {
              id: "place.1",
              place_name: "Boston, Massachusetts, United States",
              bbox: [-71.2, 42.2, -70.9, 42.4],
              center: [-71.05, 42.3],
            },
          ],
        }),
        { status: 200, headers: { "Content-Type": "application/json" } },
      ),
    );
  });

  afterEach(() => {
    vi.unstubAllEnvs();
  });

  it("navigates to map with bbox when a place is selected", async () => {
    render(<DiscoverPlaceSearch />);
    const input = screen.getByLabelText(/u\.s\. city or place/i);
    fireEvent.change(input, { target: { value: "Boston" } });

    await waitFor(() => {
      expect(
        screen.getByText("Boston, Massachusetts, United States"),
      ).toBeInTheDocument();
    });

    fireEvent.click(screen.getByText("Boston, Massachusetts, United States"));

    await waitFor(() => {
      expect(push).toHaveBeenCalled();
      const href = String(push.mock.calls[0][0]);
      expect(href).toContain("/discover/map?");
      expect(href).toContain("min_lng=-71.2");
      expect(href).toContain("max_lat=42.4");
    });
  });
});
