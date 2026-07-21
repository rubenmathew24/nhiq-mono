import { describe, it, expect, vi } from "vitest";
import { render, screen } from "@testing-library/react";
import LookupList from "@/components/dashboard/LookupList";
import type { SavedLookup } from "@/types/api";

vi.mock("next-auth/react", () => ({
  useSession: () => ({ data: null, status: "unauthenticated" }),
}));

vi.mock("next/navigation", () => ({
  useRouter: () => ({ refresh: vi.fn(), push: vi.fn() }),
}));

const mockLookup: SavedLookup = {
  user_id: "u1",
  address_id: "addr-001",
  address_normalized: "123 Main St, Austin, TX",
  looked_up_at: "2026-07-10T12:00:00Z",
  last_activity_at: "2026-07-10T12:00:00Z",
  is_favorite: false,
  overall_score: 72,
};

const favorited: SavedLookup = {
  ...mockLookup,
  address_id: "addr-002",
  is_favorite: true,
  overall_score: 88,
};

describe("LookupList", () => {
  it("shows empty state when no lookups", () => {
    render(<LookupList lookups={[]} />);
    expect(screen.getByText(/no saved lookups/i)).toBeInTheDocument();
    expect(screen.getByText(/search bar above/i)).toBeInTheDocument();
  });

  it("renders Favorites and Recent with leading score", () => {
    render(<LookupList lookups={[mockLookup]} />);
    expect(screen.getByText("Favorites")).toBeInTheDocument();
    expect(screen.getByText("Recent")).toBeInTheDocument();
    expect(
      screen.getAllByText("123 Main St, Austin, TX").length,
    ).toBeGreaterThanOrEqual(1);
    expect(screen.getAllByText("72").length).toBeGreaterThanOrEqual(1);
  });

  it("shows favorite indicator when favorited", () => {
    render(<LookupList lookups={[favorited]} />);
    expect(screen.getAllByLabelText("Favorited").length).toBeGreaterThanOrEqual(1);
    expect(screen.getAllByText("88").length).toBeGreaterThanOrEqual(1);
  });

  it("renders a link to the report for each lookup", () => {
    render(<LookupList lookups={[mockLookup]} />);
    const links = screen.getAllByRole("link");
    expect(links[0]).toHaveAttribute("href", "/report/addr-001");
  });
});
