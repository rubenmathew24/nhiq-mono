import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, fireEvent, waitFor } from "@testing-library/react";
import LookupList from "@/components/dashboard/LookupList";
import type { SavedLookup } from "@/types/api";

const refresh = vi.fn();
const apiFetch = vi.fn();

vi.mock("next-auth/react", () => ({
  useSession: () => ({
    data: { accessToken: "tok" },
    status: "authenticated",
  }),
}));

vi.mock("next/navigation", () => ({
  useRouter: () => ({ refresh, push: vi.fn() }),
}));

vi.mock("@/lib/api", async () => {
  const actual = await vi.importActual<typeof import("@/lib/api")>("@/lib/api");
  return {
    ...actual,
    apiFetch: (...args: unknown[]) => apiFetch(...args),
  };
});

const base: SavedLookup = {
  user_id: "u1",
  address_id: "addr-menu",
  address_normalized: "55 Menu St",
  looked_up_at: "2026-07-10T12:00:00Z",
  last_activity_at: "2026-07-10T12:00:00Z",
  is_favorite: false,
  overall_score: 61,
};

const favorited: SavedLookup = {
  ...base,
  address_id: "addr-fav",
  is_favorite: true,
  overall_score: 90,
};

describe("LookupList overflow menu", () => {
  beforeEach(() => {
    apiFetch.mockReset();
    refresh.mockReset();
  });

  it("hides Delete while favorited and shows guidance", async () => {
    render(<LookupList lookups={[favorited]} />);
    const buttons = screen.getAllByLabelText("Address actions");
    fireEvent.click(buttons[0]);
    expect(screen.getByText("Unfavorite")).toBeInTheDocument();
    expect(
      screen.getByText(/unfavorite before you can delete/i),
    ).toBeInTheDocument();
    expect(screen.queryByText("Delete")).not.toBeInTheDocument();
  });

  it("closes the entire menu when Cancel is clicked on confirm", async () => {
    render(<LookupList lookups={[base]} />);
    fireEvent.click(screen.getByLabelText("Address actions"));
    fireEvent.click(screen.getByText("Delete"));
    expect(screen.getByText(/remove this address/i)).toBeInTheDocument();
    fireEvent.click(screen.getByText("Cancel"));
    await waitFor(() => {
      expect(screen.queryByText("Favorite")).not.toBeInTheDocument();
      expect(screen.queryByText(/remove this address/i)).not.toBeInTheDocument();
    });
  });

  it("closes the menu on outside click", async () => {
    render(
      <div>
        <button type="button">Outside</button>
        <LookupList lookups={[base]} />
      </div>,
    );
    fireEvent.click(screen.getByLabelText("Address actions"));
    expect(screen.getByText("Favorite")).toBeInTheDocument();
    fireEvent.mouseDown(screen.getByText("Outside"));
    await waitFor(() => {
      expect(screen.queryByText("Favorite")).not.toBeInTheDocument();
    });
  });
});
