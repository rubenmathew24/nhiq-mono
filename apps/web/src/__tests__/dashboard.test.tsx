import { describe, it, expect } from "vitest";
import { render, screen } from "@testing-library/react";
import LookupList from "@/components/dashboard/LookupList";
import type { SavedLookup } from "@/types/api";

const mockLookup: SavedLookup = {
  user_id: "u1",
  address_id: "addr-001",
  address_normalized: "123 Main St, Austin, TX",
  looked_up_at: "2026-07-10T12:00:00Z",
};

describe("LookupList", () => {
  it("shows empty state when no lookups", () => {
    render(<LookupList lookups={[]} />);
    expect(screen.getByText(/no saved lookups/i)).toBeInTheDocument();
    expect(screen.getByText(/search bar above/i)).toBeInTheDocument();
  });

  it("renders a lookup row", () => {
    render(<LookupList lookups={[mockLookup]} />);
    expect(screen.getByText("123 Main St, Austin, TX")).toBeInTheDocument();
  });

  it("renders a link to the report for each lookup", () => {
    render(<LookupList lookups={[mockLookup]} />);
    const link = screen.getByRole("link");
    expect(link).toHaveAttribute("href", "/report/addr-001");
  });
});
