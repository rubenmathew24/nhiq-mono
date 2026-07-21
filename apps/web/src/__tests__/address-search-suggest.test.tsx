import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import { render, screen, fireEvent, waitFor } from "@testing-library/react";
import AddressSearch from "@/components/search/AddressSearch";

const push = vi.fn();

vi.mock("next/navigation", () => ({
  useRouter: () => ({ push }),
}));

vi.mock("next-auth/react", () => ({
  useSession: () => ({ data: null, status: "unauthenticated" }),
}));

vi.mock("@/lib/api", async () => {
  const actual = await vi.importActual<typeof import("@/lib/api")>("@/lib/api");
  return {
    ...actual,
    apiFetch: vi.fn().mockResolvedValue({
      address_id: "addr-xyz",
      status: "ready",
      address_normalized: "1 Main St",
    }),
  };
});

describe("AddressSearch suggestions", () => {
  beforeEach(() => {
    push.mockClear();
    vi.stubEnv("NEXT_PUBLIC_MAPBOX_TOKEN", "pk.test");
    globalThis.fetch = vi.fn().mockResolvedValue(
      new Response(
        JSON.stringify({
          features: [
            { id: "place.1", place_name: "1600 Pennsylvania Ave NW, Washington, DC" },
          ],
        }),
        { status: 200, headers: { "Content-Type": "application/json" } },
      ),
    );
  });

  afterEach(() => {
    vi.unstubAllEnvs();
  });

  it("shows a suggestion and submits when selected", async () => {
    const { apiFetch } = await import("@/lib/api");
    render(<AddressSearch />);
    const input = screen.getByLabelText(/u\.s\. address/i);
    fireEvent.change(input, { target: { value: "1600 Penn" } });

    await waitFor(() => {
      expect(
        screen.getByText("1600 Pennsylvania Ave NW, Washington, DC"),
      ).toBeInTheDocument();
    });

    fireEvent.click(screen.getByText("1600 Pennsylvania Ave NW, Washington, DC"));

    await waitFor(() => {
      expect(apiFetch).toHaveBeenCalled();
      expect(push).toHaveBeenCalledWith("/report/addr-xyz");
    });
  });
});
